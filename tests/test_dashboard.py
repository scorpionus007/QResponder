"""Live processing dashboard / event-stream tests (Phase 8 D). Offline."""

import time
from pathlib import Path

import pytest

from qresponder.config import Config
from qresponder.core.pipeline import run_pipeline
from qresponder.llm.mock import MockProvider

FIX = Path(__file__).parent / "fixtures"


def test_run_pipeline_emits_ordered_event_sequence():
    events = []
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    result = run_pipeline(str(FIX / "sample.xlsx"), str(FIX / "kb"), str(FIX / "qa.yaml"),
                          cfg, scope_tags=["soc2"], provider=MockProvider(),
                          on_event=events.append)
    types = [e["type"] for e in events]
    # Ordered: file_started → parsed → ... per-question ... → file_done.
    assert types[0] == "file_started"
    assert types[1] == "parsed"
    assert types[-1] == "file_done"
    assert "question_started" in types and "question_done" in types

    # Counts reconcile with the results.
    n_questions = next(e for e in events if e["type"] == "parsed")["questions"]
    assert n_questions == len(result.results)
    assert types.count("question_done") == len(result.results)
    fd = events[-1]
    answered = sum(1 for r in result.results if r.status.value == "answered")
    assert fd["answered"] == answered
    assert fd["flagged"] == len(result.results) - answered
    # Decision events appear (grounded path is visible).
    assert any(t in types for t in ("tier1_reuse", "generated", "attachment"))


def test_error_event_on_bad_file(tmp_path):
    bad = tmp_path / "broken.xlsx"
    bad.write_bytes(b"not really xlsx")
    events = []
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    with pytest.raises(Exception):
        run_pipeline(str(bad), None, None, cfg, provider=MockProvider(), on_event=events.append)
    assert any(e["type"] == "error" for e in events)


# --- web batch-stream ---

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.web.app import create_app  # noqa: E402

INCIDENT_MD = "Tags: soc2\n\nWe maintain a documented incident response plan."


def _client(tmp_path):
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    return TestClient(create_app(cfg))


def test_batch_stream_emits_events_and_zip(tmp_path):
    client = _client(tmp_path)
    wid = client.post("/api/workspaces", json={"name": "W"}).json()["id"]
    client.post(f"/api/workspaces/{wid}/kb",
                files=[("files", ("incident.md", INCIDENT_MD, "text/markdown"))])
    data = (FIX / "sample.xlsx").read_bytes()
    resp = client.post(
        f"/api/workspaces/{wid}/batch-stream",
        files=[("files", ("q1.xlsx", data, "application/octet-stream")),
               ("files", ("q2.xlsx", data, "application/octet-stream"))],
    ).json()
    bid = resp["batch_id"]
    assert resp["n_files"] == 2

    for _ in range(80):
        snap = client.get(f"/api/runs/{bid}/events").json()
        if snap["status"] in ("done", "error"):
            break
        time.sleep(0.05)
    snap = client.get(f"/api/runs/{bid}/events").json()
    assert snap["status"] == "done", snap
    types = [e["type"] for e in snap["events"]]
    assert types.count("file_started") == 2
    assert types.count("file_done") == 2
    assert snap["zip"]
    # ZIP of filled originals is downloadable.
    dl = client.get(f"/api/runs/{bid}/download/{snap['zip']}")
    assert dl.status_code == 200 and dl.content[:2] == b"PK"
