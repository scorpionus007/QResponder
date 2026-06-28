"""Embeddings interface, defaulting to a LOCAL model so the fully-local path
makes zero external network calls (§4.7, §12). sentence-transformers is imported
lazily; wired into retrieval in Phase 1.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class LocalEmbedder:
    """Local sentence-transformers embedder. First run downloads the model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # pragma: no cover - import guard
                raise RuntimeError(
                    "sentence-transformers is not installed. "
                    'Install it with: pip install "qresponder[retrieval]"'
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [list(map(float, v)) for v in vecs]
