"""The flywheel (Scrut L6, §10) — approve reviewed answers into the Library.

Every human-accepted (or edited-then-accepted) answer becomes a versioned
approved Answer Library entry, so Tier-1 coverage compounds and accuracy climbs
with use — independent of the model. Near-identical questions are de-duplicated:
an existing entry is updated and its version bumped rather than appended.

File-safe: writes to a temp file in the same directory then atomically replaces
the target, so existing entries are never lost on a crash.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import yaml

from ..kb.base import lexical_similarity
from ..kb.library import AUTO_REUSE_THRESHOLD, AnswerLibrary, LibraryEntry
from ..kb.tags import normalize_tags
from ..models import AnswerType, QuestionnaireResult, ReviewReason, Status

log = logging.getLogger("qresponder.flywheel")


def _accepted(result: QuestionnaireResult) -> list:
    """Items the reviewer accepted: ANSWERED with a real text answer. This
    naturally includes LIBRARY_CANDIDATE / AMBIGUOUS items the human resolved
    (resolving them means flipping status to ANSWERED with a chosen answer).
    Attachments are excluded — they are files, not reusable Q&A text."""
    out = []
    for r in result.results:
        if r.answer_type == AnswerType.ATTACHMENT:
            continue
        if r.status == Status.ANSWERED and r.answer and r.answer.strip():
            out.append(r)
    return out


def _entries_to_dicts(entries: list[LibraryEntry]) -> list[dict]:
    rows = []
    for e in entries:
        rows.append(
            {
                "question": e.question,
                "answer": e.answer,
                "tags": e.tags,
                "approved_by": e.approved_by,
                "version": e.version,
            }
        )
    return rows


def _safe_write_yaml(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(rows, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)
        os.replace(tmp, path)  # atomic
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def approve(
    results_path: str | Path,
    qa_path: str | Path,
    approved_by: str | None = None,
    extra_tags=None,
) -> dict:
    """Append accepted answers to the Answer Library, de-duped + versioned."""
    result = QuestionnaireResult.model_validate_json(
        Path(results_path).read_text(encoding="utf-8")
    )
    library = AnswerLibrary.load(qa_path)  # empty if the file doesn't exist yet
    tags = normalize_tags(extra_tags)

    added = updated = 0
    for r in _accepted(result):
        question = r.question_text.strip()
        answer = r.answer.strip()

        # Dedup at the auto-reuse band: same question -> update + bump version.
        existing = None
        for e in library.entries:
            if lexical_similarity(question, e.question) >= AUTO_REUSE_THRESHOLD:
                existing = e
                break

        if existing is not None:
            existing.answer = answer
            existing.version += 1
            if tags:
                existing.tags = sorted(set(existing.tags) | set(tags))
            if approved_by:
                existing.approved_by = approved_by
            updated += 1
        else:
            library.entries.append(
                LibraryEntry(
                    question=question,
                    answer=answer,
                    tags=tags,
                    approved_by=approved_by,
                    version=1,
                )
            )
            added += 1

    _safe_write_yaml(Path(qa_path), _entries_to_dicts(library.entries))
    log.info("Flywheel: %d added, %d updated; library now %d entries", added, updated, len(library.entries))
    return {"added": added, "updated": updated, "total": len(library.entries)}
