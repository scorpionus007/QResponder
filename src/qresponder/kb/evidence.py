"""Evidence vault index (Scrut L5, §9) — Phase 2.

Indexes an evidence directory so attachment requests ("attach your SOC 2
report") can be resolved to a real file. Each item carries: filename, a short
text head (first page / extracted head, best-effort), tags (from filename
tokens), and a version / date parsed from the filename where present. Tag-scoped
(§5.3). All offline — no external calls.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import BaseModel, Field

from .tags import in_scope, normalize_tags

log = logging.getLogger("qresponder.evidence")

_VERSION_RE = re.compile(r"[._\-\s]v(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
_HEAD_CHARS = 800


def _humanize(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[._\-]+", " ", stem).strip()


def _filename_tags(filename: str) -> list[str]:
    toks = [t.lower() for t in _TOKEN_RE.findall(Path(filename).stem) if len(t) > 1]
    # Normalize a couple of common spellings so "SOC 2" matches a "soc2" scope.
    norm = set(toks)
    if "soc" in norm and "2" in toks:
        norm.add("soc2")
    return sorted(norm)


def _head_text(path: Path) -> str:
    """Best-effort first-page/head text via the ingest loaders; '' on failure."""
    try:
        from ..ingest.base import load_document

        doc = load_document(path)
        text = " ".join(el.text for el in doc.elements[:40])
        return text[:_HEAD_CHARS]
    except Exception:  # noqa: BLE001 - binary/unsupported evidence still indexes by name
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:_HEAD_CHARS]
        except Exception:  # noqa: BLE001
            return ""


class EvidenceItem(BaseModel):
    filename: str
    path: str
    snippet: str = ""
    tags: list[str] = Field(default_factory=list)
    version: int | None = None
    date: str | None = None
    doc_type: str = ""

    def match_text(self) -> str:
        return f"{_humanize(self.filename)} {self.snippet}".strip()


class EvidenceIndex:
    def __init__(self, items: list[EvidenceItem] | None = None):
        self.items: list[EvidenceItem] = items or []

    @classmethod
    def load(cls, evidence_dir: str | Path | None) -> "EvidenceIndex":
        items: list[EvidenceItem] = []
        if not evidence_dir:
            return cls(items)
        d = Path(evidence_dir)
        if not d.exists():
            return cls(items)
        for fp in sorted(d.rglob("*")):
            if not fp.is_file():
                continue
            name = fp.name
            vmatch = _VERSION_RE.search(name)
            dmatch = _DATE_RE.search(name)
            items.append(
                EvidenceItem(
                    filename=name,
                    path=str(fp),
                    snippet=_head_text(fp),
                    tags=_filename_tags(name),
                    version=int(vmatch.group(1)) if vmatch else None,
                    date=dmatch.group(1) if dmatch else None,
                    doc_type=fp.suffix.lower().lstrip("."),
                )
            )
        log.info("Indexed %d evidence file(s) from %s", len(items), evidence_dir)
        return cls(items)

    def scoped(self, scope_tags=None) -> list[EvidenceItem]:
        return [i for i in self.items if in_scope(i.tags, scope_tags)]
