"""Tier 1 — the Answer Library (§5.1, the AUTHORITY).

Human-approved Q&A. A strong match here is reused (lightly reframed) and marked
source_tier=1 — ~100% correct by construction. Always tried before generation.
Tag-scoped (§5.3). Phase 0 matches lexically; the threshold is deliberately
conservative so only strong matches auto-reuse.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from .base import lexical_similarity
from .tags import in_scope, normalize_tags

# A match at/above this score is treated as the same question (auto-reuse).
DEFAULT_MATCH_THRESHOLD = 0.62


class LibraryEntry(BaseModel):
    question: str
    answer: str
    tags: list[str] = Field(default_factory=list)
    approved_by: str | None = None
    version: int = 1


class AnswerLibrary:
    def __init__(self, entries: list[LibraryEntry] | None = None):
        self.entries: list[LibraryEntry] = entries or []

    @classmethod
    def load(cls, path: str | Path | None) -> "AnswerLibrary":
        if path is None:
            return cls([])
        p = Path(path)
        if not p.exists():
            return cls([])
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or []
        entries: list[LibraryEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            entries.append(
                LibraryEntry(
                    question=str(item.get("question", "")).strip(),
                    answer=str(item.get("answer", "")).strip(),
                    tags=normalize_tags(item.get("tags")),
                    approved_by=item.get("approved_by"),
                    version=int(item.get("version", 1)),
                )
            )
        return cls([e for e in entries if e.question and e.answer])

    def match(
        self,
        question_text: str,
        scope_tags=None,
        threshold: float = DEFAULT_MATCH_THRESHOLD,
    ) -> tuple[LibraryEntry, float] | None:
        """Return the best in-scope entry and its score if >= threshold."""
        best: tuple[LibraryEntry, float] | None = None
        for entry in self.entries:
            if not in_scope(entry.tags, scope_tags):
                continue
            score = lexical_similarity(question_text, entry.question)
            if best is None or score > best[1]:
                best = (entry, score)
        if best is not None and best[1] >= threshold:
            return best
        return None
