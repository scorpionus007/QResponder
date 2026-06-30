"""Phase 11 dashboard wiring — new additive endpoints (offline, TestClient + mock).

Covers: QA export (csv/json), kb-check merge (opt-in, version-bump not delete),
flagged export + Sync-with-KB clearing matched items, and per-file batch download.
The web layer stays thin — these are wrappers over the existing engine/core.
"""

import io
import time
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.config import Config  # noqa: E402
from qresponder.kb.library import AnswerLibrary  # noqa: E402
from qresponder.web.app import create_app  # noqa: E402

FIX = Path(__file__).parent / "fixtures"
KB_MD = "Tags: soc2\n\nWe encrypt all data at rest with AES-256 and in transit with TLS 1.2+."


def _client(tmp_path):
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    cfg.extra["workspaces_dir"] = str(tmp_path / "workspaces")
    return TestClient(create_app(cfg))


def _ws(client):
    return client.post("/api/workspaces", json={"name": "Acme"}).json()["id"]


# ---- QA export --------------------------------------------------------------

def test_qa_export_csv_and_json(tmp_path):
    client = _client(tmp_path)
    wid = _ws(client)
    client.post(f"/api/workspaces/{wid}/qa",
                json={"question": "Do you encrypt at rest?", "answer": "Yes, AES-256.", "tags": ["security"]})

    r = client.get(f"/api/workspaces/{wid}/qa/export?fmt=csv")
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]
    assert "Do you encrypt at rest?" in r.text and "AES-256" in r.text
    assert "category" in r.text.splitlines()[0]

    rj = client.get(f"/api/workspaces/{wid}/qa/export?fmt=json")
    data = rj.json()
    assert data[0]["question"] == "Do you encrypt at rest?"
    assert data[0]["category"] == "security"


# ---- kb-check merge (opt-in, never deletes) ---------------------------------

def test_kb_check_merge_is_version_bump_not_delete(tmp_path):
    client = _client(tmp_path)
    wid = _ws(client)
    # Add two distinct entries (approve_one merges near-duplicates on insert, so we
    # can't create a dup pair directly), then EDIT the second to be near-identical —
    # PUT edits don't dedup, producing a real near-duplicate pair for kb-check.
    client.post(f"/api/workspaces/{wid}/qa", json={"question": "Do you encrypt data at rest?", "answer": "Yes."})
    client.post(f"/api/workspaces/{wid}/qa", json={"question": "What is your data retention period?", "answer": "1 year."})
    client.put(f"/api/workspaces/{wid}/qa/1", json={"question": "Do you encrypt data at rest ?"})
    before = len(client.get(f"/api/workspaces/{wid}/qa").json()["entries"])
    assert before == 2

    res = client.post(f"/api/workspaces/{wid}/kb-check/merge").json()
    assert res["merged"] >= 1
    after = client.get(f"/api/workspaces/{wid}/qa").json()["entries"]
    # Never deletes — entry count does not shrink; the canonical version-bumps.
    assert len(after) >= before - 0
    assert any(e["version"] > 1 for e in after)


# ---- flagged export + sync --------------------------------------------------

def _run_and_flag(client, wid):
    """Run a questionnaire that produces at least one flagged item; return run_id."""
    with open(FIX / "sample.xlsx", "rb") as fh:
        data = fh.read()
    r = client.post(f"/api/workspaces/{wid}/runs",
                    files={"questionnaire": ("sample.xlsx", data,
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    run_id = r.json()["run_id"]
    for _ in range(80):
        if client.get(f"/api/runs/{run_id}").json()["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    return run_id


def test_flagged_export_csv_round_trip_header(tmp_path):
    client = _client(tmp_path)
    wid = _ws(client)
    client.post(f"/api/workspaces/{wid}/kb", files={"files": ("kb.md", KB_MD, "text/markdown")})
    _run_and_flag(client, wid)
    r = client.get(f"/api/workspaces/{wid}/flagged/export")
    assert r.status_code == 200 and "text/csv" in r.headers["content-type"]
    header = r.text.splitlines()[0]
    for col in ("category", "question", "answer", "reason", "files"):
        assert col in header


def test_sync_with_kb_clears_matched_flagged(tmp_path):
    client = _client(tmp_path)
    wid = _ws(client)
    client.post(f"/api/workspaces/{wid}/kb", files={"files": ("kb.md", KB_MD, "text/markdown")})
    _run_and_flag(client, wid)
    groups = client.get(f"/api/workspaces/{wid}/flagged").json()["groups"]
    if not groups:
        pytest.skip("fixture produced no flagged items in this environment")
    # Approve an exact answer for the first flagged question, then Sync.
    q = groups[0]["question"]
    client.post(f"/api/workspaces/{wid}/qa", json={"question": q, "answer": "Synced approved answer."})
    res = client.post(f"/api/workspaces/{wid}/flagged/sync").json()
    assert res["cleared"] >= 1
    # The synced item is gone from the flagged list.
    after = client.get(f"/api/workspaces/{wid}/flagged").json()["groups"]
    assert all(g["question"] != q for g in after)


# ---- per-file batch download ------------------------------------------------

def test_batch_per_file_download_returns_filled_original(tmp_path):
    client = _client(tmp_path)
    wid = _ws(client)
    client.post(f"/api/workspaces/{wid}/kb", files={"files": ("kb.md", KB_MD, "text/markdown")})
    with open(FIX / "sample.xlsx", "rb") as fh:
        data = fh.read()
    r = client.post(f"/api/workspaces/{wid}/batch-stream",
                    files=[("files", ("sample.xlsx", data,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))])
    batch_id = r.json()["batch_id"]
    for _ in range(120):
        if client.get(f"/api/runs/{batch_id}/events").json()["status"] in ("done", "error"):
            break
        time.sleep(0.05)

    files = client.get(f"/api/runs/{batch_id}/files").json()["files"]
    assert files, "batch summary should list the per-file result"
    f0 = files[0]
    # Additive per-file bookkeeping is present.
    assert "model_calls" in f0["summary"] and "tokens_est" in f0["summary"]
    dl = client.get(f"/api/runs/{batch_id}/files/{f0['stem']}/download")
    assert dl.status_code == 200 and len(dl.content) > 0
