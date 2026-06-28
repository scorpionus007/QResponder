"""Cross-encoder reranker interface, defaulting to a LOCAL model (§7).

Reranking is the highest-ROI precision gain: retrieve ~20, rerank, pass top
3-5 to the LLM. Watch the 512-token truncation limit — keep chunks short enough
that the reranker sees the whole chunk. Wired into retrieval in Phase 1.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, docs: list[str]) -> list[tuple[int, float]]: ...


class LocalReranker:
    """Local cross-encoder reranker. First run downloads the model."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:  # pragma: no cover - import guard
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    'Install it with: pip install "qresponder[retrieval]"'
                ) from exc
            self._model = CrossEncoder(self.model_name, max_length=512)
        return self._model

    def rerank(self, query: str, docs: list[str]) -> list[tuple[int, float]]:
        """Return (original_index, score) sorted by descending relevance."""
        if not docs:
            return []
        model = self._load()
        scores = model.predict([(query, d) for d in docs])
        ranked = sorted(enumerate(float(s) for s in scores), key=lambda x: x[1], reverse=True)
        return ranked
