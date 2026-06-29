"""Attachment resolution tests (C2, §9). Offline (lexical similarity, no model)."""

from pathlib import Path

from qresponder.config import Config
from qresponder.core.attachments import resolve_attachment
from qresponder.core.orchestrate import orchestrate
from qresponder.kb.evidence import EvidenceIndex, EvidenceItem
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.llm.mock import MockProvider
from qresponder.models import AnswerType, Question, ReviewReason, Status

FIX = Path(__file__).parent / "fixtures"


def _evidence():
    return EvidenceIndex.load(FIX / "evidence")


def test_evidence_index_parses_version_and_tags():
    idx = _evidence()
    soc2 = next(i for i in idx.items if i.filename.startswith("SOC2"))
    assert soc2.version == 2
    assert "soc2" in soc2.tags
    annual = next(i for i in idx.items if "2025" in i.filename)
    assert annual.date is None  # no full YYYY-MM-DD in name; year alone isn't a date


def test_attachment_resolves_clear_winner():
    q = Question(id="q1", text="Please attach your most recent SOC 2 Type II report.",
                 answer_type=AnswerType.ATTACHMENT)
    r = resolve_attachment(q, _evidence(), Config(), scope_tags=["soc2"])
    assert r.status == Status.ANSWERED
    assert r.attachment_path and r.attachment_path.endswith("SOC2_Type_II_Report_v2.md")
    assert r.answer == "SOC2_Type_II_Report_v2.md"
    assert r.source_tier == 3


def test_attachment_underspecified_returns_candidates():
    # Two near-identical annual reports -> no clear winner -> candidates.
    q = Question(id="q1", text="Please attach the annual security report.",
                 answer_type=AnswerType.ATTACHMENT)
    r = resolve_attachment(q, _evidence(), Config(), scope_tags=None)
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.ATTACHMENT_UNRESOLVED
    assert len(r.attachment_candidates) >= 2
    assert any("Annual_Security_Report" in c for c in r.attachment_candidates)


def test_solo_weak_candidate_is_flagged_not_attached():
    """SH2: a single, weakly-related evidence file must NOT auto-attach just
    because there is no runner-up — it's surfaced as a candidate."""
    idx = EvidenceIndex([
        EvidenceItem(filename="Office_Floor_Plan.md", path="/x/Office_Floor_Plan.md",
                     snippet="Floor plan of the office building.", tags=[])
    ])
    q = Question(id="q1", text="Please attach your SOC 2 Type II audit report.",
                 answer_type=AnswerType.ATTACHMENT)
    r = resolve_attachment(q, idx, Config(), scope_tags=None)
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.ATTACHMENT_UNRESOLVED
    assert not r.attachment_path
    assert "Office_Floor_Plan.md" in r.attachment_candidates


def test_solo_strong_candidate_resolves():
    """SH2: a single, strongly-matching file still auto-resolves."""
    idx = EvidenceIndex([
        EvidenceItem(filename="SOC2_Type_II_Report_v2.md", path="/x/SOC2_Type_II_Report_v2.md",
                     snippet="SOC 2 Type II report covering security controls.",
                     tags=["soc2"], version=2)
    ])
    q = Question(id="q1", text="Please attach your SOC 2 Type II report.",
                 answer_type=AnswerType.ATTACHMENT)
    r = resolve_attachment(q, idx, Config(), scope_tags=["soc2"])
    assert r.status == Status.ANSWERED
    assert r.attachment_path and r.attachment_path.endswith("SOC2_Type_II_Report_v2.md")


def test_orchestrate_routes_attachment_to_resolver_when_evidence_present():
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    q = [Question(id="q1", text="Please attach your SOC 2 Type II report.", answer_type=AnswerType.ATTACHMENT)]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), InContextKB([]), cfg,
                    scope_tags=["soc2"], evidence=_evidence())[0]
    assert r.status == Status.ANSWERED
    assert r.attachment_path


def test_orchestrate_without_evidence_keeps_flag_behavior():
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    q = [Question(id="q1", text="Please attach your SOC 2 report.", answer_type=AnswerType.ATTACHMENT)]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), InContextKB([]), cfg, scope_tags=["soc2"])[0]
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.ATTACHMENT_UNRESOLVED
    assert not r.attachment_path