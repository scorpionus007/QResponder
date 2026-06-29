"""Cross-source conflict detection tests (D1, §5.2). MockProvider, no network."""

from qresponder.config import Config
from qresponder.core.conflicts import detect_conflicts
from qresponder.kb.library import AnswerLibrary, LibraryEntry
from qresponder.llm.mock import MockProvider
from qresponder.models import (
    AnswerResult,
    AnswerType,
    Confidence,
    ReviewReason,
    Status,
)


def _answered(qid, question, answer, tier=2, atype=AnswerType.YES_NO):
    return AnswerResult(
        question_id=qid,
        question_text=question,
        answer=answer,
        answer_type=atype,
        confidence=Confidence.MEDIUM,
        status=Status.ANSWERED,
        source_tier=tier,
    )


def test_two_run_answers_contradict_both_flagged():
    a = _answered("q1", "Do you encrypt data at rest?", "Yes, all data at rest is encrypted.")
    b = _answered("q2", "Is data at rest encrypted?", "No, data at rest is not encrypted.")
    results = [a, b]
    detect_conflicts(results, AnswerLibrary([]), MockProvider(), Config())
    assert a.review_reason == ReviewReason.CONFLICT
    assert b.review_reason == ReviewReason.CONFLICT
    assert a.status == Status.NEEDS_REVIEW and b.status == Status.NEEDS_REVIEW
    assert a.conflict_with and b.conflict_with
    assert a.confidence == Confidence.LOW


def test_generated_contradicting_tier1_is_flagged():
    lib = AnswerLibrary([
        LibraryEntry(question="Do you enforce MFA for employees?",
                     answer="Yes, MFA is enforced for all employees.",
                     tags=["soc2"], approved_by="security", version=1)
    ])
    gen = _answered("q1", "Is MFA enforced for employees?", "No, MFA is not enforced.")
    results = [gen]
    detect_conflicts(results, lib, MockProvider(), Config())
    assert gen.review_reason == ReviewReason.CONFLICT
    assert gen.conflict_with and "Answer Library" in gen.conflict_with


def test_value_conflict_detected():
    a = _answered("q1", "What TLS version do you require?", "We require TLS 1.2 or higher.", atype=AnswerType.TEXT)
    b = _answered("q2", "What is your minimum TLS version?", "We require TLS 1.3 only.", atype=AnswerType.TEXT)
    detect_conflicts([a, b], AnswerLibrary([]), MockProvider(), Config())
    assert a.review_reason == ReviewReason.CONFLICT
    assert b.review_reason == ReviewReason.CONFLICT


def test_unrelated_questions_not_flagged():
    a = _answered("q1", "Do you encrypt data at rest?", "Yes.")
    b = _answered("q2", "Where is your headquarters located?", "No.")  # different topic
    detect_conflicts([a, b], AnswerLibrary([]), MockProvider(), Config())
    assert a.review_reason == ReviewReason.NONE
    assert b.review_reason == ReviewReason.NONE
    assert a.status == Status.ANSWERED and b.status == Status.ANSWERED


def test_tier1_reuse_never_flagged():
    """A Tier-1 reused answer must never be flagged/overridden, even if a
    generated answer contradicts it — only the generated one is flagged."""
    tier1 = _answered("q1", "Do you encrypt data at rest?", "Yes, encrypted at rest.", tier=1)
    gen = _answered("q2", "Is data at rest encrypted?", "No, not encrypted at rest.", tier=2)
    detect_conflicts([tier1, gen], AnswerLibrary([]), MockProvider(), Config())
    assert tier1.review_reason == ReviewReason.NONE
    assert tier1.status == Status.ANSWERED
    assert gen.review_reason == ReviewReason.CONFLICT


def test_disabled_by_config():
    a = _answered("q1", "Do you encrypt data at rest?", "Yes.")
    b = _answered("q2", "Is data at rest encrypted?", "No.")
    detect_conflicts([a, b], AnswerLibrary([]), MockProvider(), Config(detect_conflicts=False))
    assert a.review_reason == ReviewReason.NONE and b.review_reason == ReviewReason.NONE
