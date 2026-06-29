"""Faithfulness verification + confidence rule tests (B2). No network."""

from qresponder.config import Config
from qresponder.core.confidence import decide_confidence, grounding_score
from qresponder.core.faithfulness import verify_results
from qresponder.core.orchestrate import orchestrate
from qresponder.kb.base import KBChunk
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.llm.mock import MockProvider
from qresponder.models import (
    AnswerResult,
    AnswerType,
    Citation,
    Confidence,
    Question,
    ReviewReason,
    Status,
)

_ENC = "All data at rest is encrypted using AES-256 with keys in KMS."


def _generated_answered(qid="q1", answer="We are ISO 27001 certified."):
    return AnswerResult(
        question_id=qid,
        question_text="Are you certified?",
        answer=answer,
        answer_type=AnswerType.TEXT,
        citations=[Citation(source="kb", snippet="ISO 27001 certification audited annually")],
        confidence=Confidence.MEDIUM,
        status=Status.ANSWERED,
        source_tier=2,
    )


def test_faithfulness_flags_unentailed():
    r = _generated_answered()
    provider = MockProvider(responses=['[{"id":"q1","faithful":false,"unsupported_claims":["no audit date"]}]'])
    verify_results(provider, [r], Config(verify_faithfulness=True))
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.FAITHFULNESS_FAIL
    assert r.confidence == Confidence.LOW
    assert r.citations[0].faithful is False
    assert r.missing_info and "faithfulness" in r.missing_info.lower()


def test_faithfulness_keeps_entailed():
    r = _generated_answered()
    provider = MockProvider(responses=['[{"id":"q1","faithful":true,"unsupported_claims":[]}]'])
    verify_results(provider, [r], Config(verify_faithfulness=True))
    assert r.status == Status.ANSWERED
    assert r.citations[0].faithful is True


def test_faithfulness_exempts_tier1():
    """F5: Tier-1 results are never sent to the judge."""
    tier1 = AnswerResult(
        question_id="q1",
        question_text="Encrypt at rest?",
        answer="Yes, AES-256.",
        answer_type=AnswerType.YES_NO,
        citations=[Citation(source="Answer Library", snippet="Yes, AES-256.", faithful=True)],
        confidence=Confidence.HIGH,
        status=Status.ANSWERED,
        source_tier=1,
    )
    provider = MockProvider()  # would record any call
    verify_results(provider, [tier1], Config(verify_faithfulness=True))
    assert provider.calls == []  # judge never invoked
    assert tier1.status == Status.ANSWERED
    assert tier1.confidence == Confidence.HIGH


def test_faithfulness_disabled_skips_check():
    r = _generated_answered()
    provider = MockProvider()
    verify_results(provider, [r], Config(verify_faithfulness=False))
    assert provider.calls == []
    assert r.status == Status.ANSWERED
    assert r.citations[0].faithful is None  # left unverified


def _incontext_kb():
    return InContextKB([KBChunk(source="enc.md", text=_ENC, tags=["soc2"], tier=2)])


def test_s1_incontext_strong_grounding_reaches_high():
    """S1: a faithful, strongly-grounded (verbatim) in-context answer earns HIGH
    even though there is no reranker."""
    cfg = Config(llm_provider="mock", kb_mode="in_context", verify_faithfulness=True)
    answer = ('[{"question_id":"q1","answer":"%s","answer_type":"yes_no",'
              '"citations":[{"source":"enc.md","snippet":"%s"}],'
              '"status":"answered","confidence":"low"}]' % (_ENC, _ENC))
    faith = '[{"id":"q1","faithful":true,"unsupported_claims":[]}]'
    provider = MockProvider(responses=[answer, faith])
    q = [Question(id="q1", text="Do you encrypt data at rest?", answer_type=AnswerType.YES_NO)]
    r = orchestrate(q, provider, AnswerLibrary([]), _incontext_kb(), cfg, scope_tags=["soc2"])[0]
    assert r.status == Status.ANSWERED
    assert r.grounding_score is not None and r.grounding_score >= 0.85
    assert r.confidence == Confidence.HIGH


def test_s1_incontext_weak_grounding_stays_medium():
    """S1: faithful but weakly-grounded in-context answer stays MEDIUM."""
    cfg = Config(llm_provider="mock", kb_mode="in_context", verify_faithfulness=True)
    answer = ('[{"question_id":"q1","answer":"Yes.","answer_type":"yes_no",'
              '"citations":[{"source":"enc.md","snippet":"encrypted using AES-256"}],'
              '"status":"answered","confidence":"high"}]')
    faith = '[{"id":"q1","faithful":true,"unsupported_claims":[]}]'
    provider = MockProvider(responses=[answer, faith])
    q = [Question(id="q1", text="Do you encrypt data at rest?", answer_type=AnswerType.YES_NO)]
    r = orchestrate(q, provider, AnswerLibrary([]), _incontext_kb(), cfg, scope_tags=["soc2"])[0]
    assert r.status == Status.ANSWERED
    assert r.grounding_score is not None and r.grounding_score < 0.85
    assert r.confidence == Confidence.MEDIUM


def test_grounding_score_lexical():
    assert grounding_score("foo bar baz", ["foo bar baz"]) >= 0.85
    assert (grounding_score("Yes.", ["encrypted using AES-256"]) or 0) < 0.85
    assert grounding_score("", ["x"]) is None
    assert grounding_score("x", []) is None


def test_confidence_rule():
    # Tier-1 -> HIGH regardless.
    assert decide_confidence(source_tier=1, status=Status.ANSWERED, faithful=False, retrieval_score=None) == Confidence.HIGH
    # Generated + faithful + strong retrieval -> HIGH.
    assert decide_confidence(source_tier=2, status=Status.ANSWERED, faithful=True, retrieval_score=0.8) == Confidence.HIGH
    # Generated + faithful but no/weak retrieval signal -> MEDIUM.
    assert decide_confidence(source_tier=2, status=Status.ANSWERED, faithful=True, retrieval_score=None) == Confidence.MEDIUM
    # Generated + strong retrieval but not faithful -> MEDIUM (answered) — but in
    # practice an unfaithful result is already NEEDS_REVIEW -> LOW:
    assert decide_confidence(source_tier=2, status=Status.NEEDS_REVIEW, faithful=False, retrieval_score=0.9) == Confidence.LOW
