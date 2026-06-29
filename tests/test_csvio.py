"""CSV round-trip, duplicate grouping, SME routing tests (Part E). Offline."""

import csv
from pathlib import Path

from qresponder.config import Config
from qresponder.core.csvio import export_flagged, import_answers
from qresponder.core.orchestrate import orchestrate
from qresponder.kb.base import KBChunk
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.llm.mock import MockProvider
from qresponder.models import (
    AnswerResult,
    AnswerType,
    Confidence,
    Question,
    QuestionnaireResult,
    ReviewReason,
    Status,
)


def _kb():
    return InContextKB([KBChunk(source="enc.md", text="Data at rest is encrypted with AES-256.", tags=["soc2"], tier=2)])


def test_duplicate_questions_answered_once_applied_to_all():
    cfg = Config(llm_provider="mock", kb_mode="in_context", dedup_questions=True)
    qs = [
        Question(id="q1", text="Do you encrypt data at rest?", answer_type=AnswerType.YES_NO),
        Question(id="q2", text="Do you encrypt data at rest?", answer_type=AnswerType.YES_NO),
        Question(id="q3", text="Where is your HQ located?", answer_type=AnswerType.TEXT),
    ]
    results = {r.question_id: r for r in orchestrate(qs, MockProvider(), AnswerLibrary([]), _kb(), cfg, scope_tags=["soc2"])}
    # q1 + q2 grouped under one canonical; identical answers.
    assert results["q1"].group_id == results["q2"].group_id == "q1"
    assert results["q1"].answer == results["q2"].answer
    # q3 is unrelated -> not grouped.
    assert results["q3"].group_id is None


def test_sme_owner_routing():
    cfg = Config(llm_provider="mock", kb_mode="in_context", owners={"backup": "alice"})
    qs = [Question(id="q1", text="What is the retention period for customer backups?", answer_type=AnswerType.TEXT)]
    r = orchestrate(qs, MockProvider(), AnswerLibrary([]), InContextKB([]), cfg, scope_tags=["soc2"])[0]
    assert r.status == Status.NEEDS_REVIEW
    assert r.owner == "alice"  # matched by 'backup' in the question


def _flagged_result():
    return QuestionnaireResult(source_file="q.xlsx", results=[
        AnswerResult(question_id="q1", question_text="Do you support SSO?", answer="",
                     answer_type=AnswerType.YES_NO, confidence=Confidence.LOW,
                     status=Status.NEEDS_REVIEW, review_reason=ReviewReason.UNSUPPORTED, owner="it"),
        # Near-identical to q1 (>=0.90 band) but not byte-equal, so it re-syncs
        # via Tier-1 rather than being flipped directly by the import loop.
        AnswerResult(question_id="q2", question_text="Do you support SSO?!", answer="",
                     answer_type=AnswerType.YES_NO, confidence=Confidence.LOW,
                     status=Status.NEEDS_REVIEW, review_reason=ReviewReason.UNSUPPORTED, owner="it"),
    ])


def test_csv_export_import_round_trip(tmp_path):
    result = _flagged_result()
    csv_path = tmp_path / "flagged.csv"
    export_flagged(result, csv_path)
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert [c for c in rows[0]] == ["category", "question", "answer", "reason", "owner"]
    assert len(rows) == 2

    # SME fills the first answer.
    rows[0]["answer"] = "Yes, SAML and OIDC SSO are supported."
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["category", "question", "answer", "reason", "owner"])
        w.writeheader(); w.writerows(rows)

    qa = tmp_path / "qa.yaml"
    stats = import_answers(csv_path, qa, result=result, approved_by="alice")
    assert stats["imported"] == 1
    # The library gained the approved answer.
    lib = AnswerLibrary.load(qa)
    assert any("sso" in e.question.lower() for e in lib.entries)
    # q1 flipped to ANSWERED...
    by = {r.question_id: r for r in result.results}
    assert by["q1"].status == Status.ANSWERED
    assert "SAML" in by["q1"].answer
    # ...and the near-duplicate q2 re-synced via Tier-1 against the updated library.
    assert by["q2"].status == Status.ANSWERED
    assert by["q2"].source_tier == 1
    assert stats["resynced"] == 1


def test_per_owner_csv_split(tmp_path):
    result = QuestionnaireResult(source_file="q.xlsx", results=[
        AnswerResult(question_id="q1", question_text="A?", answer="", answer_type=AnswerType.TEXT,
                     confidence=Confidence.LOW, status=Status.NEEDS_REVIEW,
                     review_reason=ReviewReason.UNSUPPORTED, owner="alice"),
        AnswerResult(question_id="q2", question_text="B?", answer="", answer_type=AnswerType.TEXT,
                     confidence=Confidence.LOW, status=Status.NEEDS_REVIEW,
                     review_reason=ReviewReason.UNSUPPORTED, owner="bob"),
    ])
    paths = export_flagged(result, tmp_path / "flagged.csv", by_owner=True)
    names = sorted(Path(p).name for p in paths)
    assert names == ["flagged_alice.csv", "flagged_bob.csv"]
