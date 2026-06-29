"""Part G tests: consistency-over-time, decomposition, query normalization."""

from pathlib import Path

from qresponder.config import Config
from qresponder.core.conflicts import detect_history_conflicts
from qresponder.core.decompose import is_compound, split_parts
from qresponder.core.history import HistoryStore
from qresponder.core.normalize import normalize_query
from qresponder.core.orchestrate import orchestrate
from qresponder.kb.base import KBChunk, lexical_similarity
from qresponder.kb.in_context import InContextKB
from qresponder.kb.library import AnswerLibrary
from qresponder.kb.retrieval import RetrievalKB
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


# --- G3: query normalization ------------------------------------------------

def test_normalize_expands_acronyms():
    out = normalize_query("Do you require MFA?")
    assert "multi-factor authentication" in out.lower()
    assert "MFA" in out  # original preserved


class _StubEmbedder:
    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


class _StubReranker:
    def rerank(self, query, docs):
        return sorted(((i, lexical_similarity(query, d)) for i, d in enumerate(docs)),
                      key=lambda x: x[1], reverse=True)


def test_acronym_query_retrieves_spelled_out_chunk():
    """G3: an acronym-only question retrieves the spelled-out KB chunk via the
    normalized (expanded) query — BM25 wins once the expansion is present."""
    chunks = [
        KBChunk(source="ac.md", text="Multi-factor authentication is enforced for all employees.", tags=["soc2"], tier=2),
        KBChunk(source="enc.md", text="Data at rest uses AES-256.", tags=["soc2"], tier=2),
    ]
    kb = RetrievalKB(chunks, embedder=_StubEmbedder(), reranker=_StubReranker(), top_n=20, top_k=5, rrf_k=60)
    cfg = Config(llm_provider="mock", kb_mode="retrieval")
    q = [Question(id="q1", text="Do you require MFA?", answer_type=AnswerType.YES_NO)]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), kb, cfg, scope_tags=["soc2"])[0]
    # The MFA chunk was retrieved + cited (audit shows it).
    sources = [c.source for c in (r.audit.retrieved if r.audit else [])]
    assert "ac.md" in sources


# --- G2: compound decomposition ---------------------------------------------

def test_split_parts_detects_multipart():
    assert is_compound("Do you encrypt data at rest, in transit, and in backups?")
    assert split_parts("Do you do A? Do you do B?") == ["Do you do A?", "Do you do B?"]
    assert not is_compound("Do you encrypt data at rest?")


def test_compound_question_yields_subanswers_and_flags_unsupported():
    # KB supports 'rest' and 'transit' but NOT 'backups'.
    kb = InContextKB([
        KBChunk(source="enc.md", text="Encryption at rest uses AES-256.", tags=["soc2"], tier=2),
        KBChunk(source="net.md", text="Encryption in transit uses TLS 1.2.", tags=["soc2"], tier=2),
    ])
    cfg = Config(llm_provider="mock", kb_mode="in_context", dedup_questions=False)
    q = [Question(id="q1", text="Do you provide encryption at rest, encryption in transit, and encryption in backups?",
                  answer_type=AnswerType.TEXT)]
    r = orchestrate(q, MockProvider(), AnswerLibrary([]), kb, cfg, scope_tags=["soc2"])[0]
    assert len(r.subanswers) == 3
    # One sub-part (backups) is unsupported -> whole item flagged.
    assert r.status == Status.NEEDS_REVIEW
    assert any(s.status != Status.ANSWERED for s in r.subanswers)
    assert r.missing_info and "backups" in r.missing_info.lower()


# --- G1: consistency over time ----------------------------------------------

def _answered(qid, q, a):
    return AnswerResult(question_id=qid, question_text=q, answer=a, answer_type=AnswerType.YES_NO,
                        confidence=Confidence.MEDIUM, status=Status.ANSWERED, source_tier=2)


def test_history_conflict_flagged():
    results = [_answered("q1", "Do you encrypt data at rest?", "No, data at rest is not encrypted.")]
    history = [{"question": "Do you encrypt data at rest?", "answer": "Yes, encrypted at rest.", "date": "2025-01-01"}]
    detect_history_conflicts(results, history, MockProvider(), Config())
    r = results[0]
    assert r.status == Status.NEEDS_REVIEW
    assert r.review_reason == ReviewReason.HISTORY_CONFLICT
    assert r.conflict_with and "2025-01-01" in r.conflict_with


def test_history_store_round_trip(tmp_path):
    store = HistoryStore(tmp_path / "history.yaml")
    assert store.load() == []
    result = QuestionnaireResult(source_file="q.xlsx",
                                 results=[_answered("q1", "Do you encrypt at rest?", "Yes.")])
    n = store.append(result, "2026-06-29")
    assert n == 1
    loaded = store.load()
    assert loaded[0]["question"] == "Do you encrypt at rest?"
    assert loaded[0]["date"] == "2026-06-29"
