"""Ambiguity / interpretation surfacing tests (C1, §8). MockProvider, no network."""

from qresponder.config import Config
from qresponder.core.orchestrate import orchestrate
from qresponder.kb.base import KBChunk
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.llm.mock import MockProvider
from qresponder.models import AnswerType, Confidence, Question, ReviewReason, Status


def _kb():
    return InContextKB([
        KBChunk(source="enc.md", text="Encryption at rest uses AES-256 with KMS-managed keys.", tags=["soc2"], tier=2),
        KBChunk(source="net.md", text="Encryption in transit uses TLS 1.2 or higher.", tags=["soc2"], tier=2),
    ])


def test_ambiguous_question_surfaces_grounded_candidates():
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    q = [
        Question(
            id="q1",
            text="Describe your encryption practices.",
            answer_type=AnswerType.TEXT,
            ambiguous=True,
            interpretations=["encryption at rest", "encryption in transit"],
        )
    ]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), _kb(), cfg, scope_tags=["soc2"])[0]
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.AMBIGUOUS
    assert r.confidence == Confidence.LOW
    assert len(r.candidates) == 2
    # Both interpretations got a grounded draft with a supported citation.
    for opt in r.candidates:
        assert opt.answer
        assert opt.citations
    assert r.missing_info and "interpretation" in r.missing_info.lower()


def test_non_ambiguous_question_unaffected():
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    q = [Question(id="q1", text="Do you encrypt data at rest?", answer_type=AnswerType.YES_NO)]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), _kb(), cfg, scope_tags=["soc2"])[0]
    assert not r.candidates
    assert r.review_reason != ReviewReason.AMBIGUOUS
