"""Cross-file flagged aggregation + one-click resolve (Phase 8 E). Offline."""

import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from qresponder.config import Config  # noqa: E402
from qresponder.kb.library import AnswerLibrary  # noqa: E402
from qresponder.models import (  # noqa: E402
    AnswerResult,
    AnswerType,
    Confidence,
    QuestionnaireResult,
    ReviewReason,
    Status,
)
from qresponder.web.app import _Job, create_app  # noqa: E402


def _client(tmp_path):
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    cfg.extra["workspaces_dir"] = str(tmp_path / "ws")
    return TestClient(create_app(cfg))


def _inject_flagged_runs(client, wid, tmp_path):
    """Three runs (files) each with the SAME flagged question + one unique one."""
    jobs = client.app.state.jobs
    for i in range(3):
        rid = f"run{i}"
        out = tmp_path / "ws" / wid / "runs" / rid
        out.mkdir(parents=True, exist_ok=True)
        job = _Job(rid, out, str(tmp_path / "ws" / wid / "qa.yaml"), [])
        job.workspace_id = wid
        job.questionnaire_path = str(out / f"file{i}.xlsx")
        job.status = "done"
        job.result = QuestionnaireResult(source_file=f"file{i}.xlsx", results=[
            AnswerResult(question_id="q1", question_text="Do you support SSO?", answer="",
                         answer_type=AnswerType.YES_NO, confidence=Confidence.LOW,
                         status=Status.NEEDS_REVIEW, review_reason=ReviewReason.UNSUPPORTED),
            AnswerResult(question_id=f"u{i}", question_text=f"Unique question {i}?", answer="",
                         answer_type=AnswerType.TEXT, confidence=Confidence.LOW,
                         status=Status.NEEDS_REVIEW, review_reason=ReviewReason.UNSUPPORTED),
        ])
        jobs[rid] = job


def test_flagged_grouped_resolved_once_trains_once(tmp_path):
    client = _client(tmp_path)
    wid = client.post("/api/workspaces", json={"name": "W"}).json()["id"]
    _inject_flagged_runs(client, wid, tmp_path)

    # The shared SSO question is grouped once (across 3 files); uniques are separate.
    groups = client.get(f"/api/workspaces/{wid}/flagged").json()["groups"]
    sso = next(g for g in groups if "sso" in g["question"].lower())
    assert sso["count"] == 3
    assert len(sso["files"]) == 3

    # Resolve it once.
    res = client.post(f"/api/workspaces/{wid}/flagged/resolve",
                      json={"question": "Do you support SSO?", "answer": "Yes — SAML & OIDC.",
                            "tags": ["soc2"]}).json()
    assert res["updated"] == 3        # all three files updated
    assert res["trained"] is True

    # All three runs now show that item ANSWERED.
    for i in range(3):
        run = client.get("/api/runs/run%d" % i).json()
        item = next(r for r in run["results"] if r["question_id"] == "q1")
        assert item["status"] == "answered"
        assert "SAML" in item["answer"]

    # Exactly ONE versioned library entry (not three).
    lib = AnswerLibrary.load(Path(tmp_path) / "ws" / wid / "qa.yaml")
    sso_entries = [e for e in lib.entries if "sso" in e.question.lower()]
    assert len(sso_entries) == 1
    assert sso_entries[0].version == 1

    # Re-resolve is idempotent: no new updates, no version bump.
    res2 = client.post(f"/api/workspaces/{wid}/flagged/resolve",
                       json={"question": "Do you support SSO?", "answer": "Yes — SAML & OIDC."}).json()
    assert res2["updated"] == 0
    assert res2["trained"] is False
    lib2 = AnswerLibrary.load(Path(tmp_path) / "ws" / wid / "qa.yaml")
    assert [e for e in lib2.entries if "sso" in e.question.lower()][0].version == 1

    # The SSO group is gone from the flagged list now.
    groups2 = client.get(f"/api/workspaces/{wid}/flagged").json()["groups"]
    assert not any("sso" in g["question"].lower() for g in groups2)
