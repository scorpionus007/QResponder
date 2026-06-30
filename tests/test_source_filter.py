"""Per-run source include/exclude tests (Phase 10 C). Offline."""

from qresponder.config import Config
from qresponder.core.pipeline import run_ask
from qresponder.kb.base import KBChunk
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.kb.tags import source_allowed
from qresponder.llm.mock import MockProvider
from qresponder.models import AnswerType, Question, Status
from qresponder.core.orchestrate import orchestrate


def test_source_allowed_logic():
    assert source_allowed("enc.md", ["soc2"], None, None)
    assert not source_allowed("enc.md", ["soc2"], None, {"enc.md"})       # excluded by name
    assert not source_allowed("enc.md", ["marketing"], None, {"marketing"})  # excluded by tag
    assert source_allowed("enc.md", ["soc2"], {"enc.md"}, None)            # included by name
    assert not source_allowed("other.md", ["x"], {"enc.md"}, None)         # include narrows out


def _kb():
    return InContextKB([
        KBChunk(source="enc.md", text="Data at rest is encrypted with AES-256.", tags=["soc2"], tier=2),
        KBChunk(source="marketing.md", text="We are the best and most secure vendor ever.", tags=["marketing"], tier=2),
    ])


def _ask(text, **kw):
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    q = [Question(id="q1", text=text, answer_type=AnswerType.YES_NO)]
    return orchestrate(q, MockProvider(), AnswerLibrary([]), _kb(), cfg, scope_tags=["soc2"], **kw)[0]


def test_excluding_grounding_source_abstains_no_fabrication():
    """NEGATIVE CASE: excluding the source that grounds the answer makes it
    abstain — it never fabricates from a different source."""
    ok = _ask("Do you encrypt data at rest with AES-256?")
    assert ok.status == Status.ANSWERED  # grounded normally

    excluded = _ask("Do you encrypt data at rest with AES-256?", exclude_sources=["enc.md"])
    assert excluded.status == Status.NEEDS_REVIEW  # grounding removed -> abstain
    assert "aes-256" not in (excluded.answer or "").lower()
    assert excluded.audit.sources_excluded == ["enc.md"]


def test_including_only_correct_source_still_answers():
    r = _ask("Do you encrypt data at rest with AES-256?", include_sources=["enc.md"])
    assert r.status == Status.ANSWERED          # the correct source is still a candidate
    assert r.citations
    assert "AES-256" in r.answer                # grounded in enc.md content
    assert r.audit.sources_used                 # cited source(s) recorded


def test_run_ask_records_used_and_excluded(tmp_path):
    from pathlib import Path

    fix = Path(__file__).parent / "fixtures"
    cfg = Config(llm_provider="mock", kb_mode="in_context")
    r = run_ask("Do you have a documented incident response plan?", str(fix / "kb"),
                str(fix / "qa.yaml"), cfg, scope_tags=["soc2"], provider=MockProvider(),
                exclude_sources=["marketing"])
    assert r.audit.sources_excluded == ["marketing"]
