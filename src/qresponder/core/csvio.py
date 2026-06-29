"""CSV round-trip for flagged items + SME per-owner split (Part E).

export_flagged: write the NEEDS_REVIEW items to a CSV an SME can fill in a
spreadsheet (category,question,answer,reason[,owner]).
import_answers: read the filled CSV back — each filled answer becomes a
human-accepted entry routed through approve_one (trains the library) and, if a
run is given, flips that run's matching item to ANSWERED. Still-flagged items are
then re-synced against the now-updated library (Tier-1 re-match).

Thin layer over approve_one + the library matcher — no new answering logic.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from ..kb.library import AUTO_REUSE_THRESHOLD, AnswerLibrary
from ..kb.base import lexical_similarity
from ..models import Citation, QuestionnaireResult, ReviewReason, Status
from .flywheel import approve_one

_COLUMNS = ["category", "question", "answer", "reason", "owner"]


def export_flagged(result: QuestionnaireResult, out_csv: str | Path, by_owner: bool = False) -> list[str]:
    flagged = [r for r in result.results if r.status == Status.NEEDS_REVIEW]
    out_csv = Path(out_csv)

    def _rows(items):
        return [
            {
                "category": r.owner or "",
                "question": r.question_text,
                "answer": r.answer or "",   # any draft to start from
                "reason": r.review_reason.value,
                "owner": r.owner or "",
            }
            for r in items
        ]

    if not by_owner:
        _write_csv(out_csv, _rows(flagged))
        return [str(out_csv)]

    # Per-owner split: flagged_<owner>.csv next to out_csv.
    groups = defaultdict(list)
    for r in flagged:
        groups[r.owner or "unassigned"].append(r)
    paths = []
    for owner, items in groups.items():
        p = out_csv.parent / f"{out_csv.stem}_{_slug(owner)}{out_csv.suffix or '.csv'}"
        _write_csv(p, _rows(items))
        paths.append(str(p))
    return paths


def _slug(name: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "unassigned"


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def import_answers(
    csv_path: str | Path,
    qa_path: str | Path,
    result: QuestionnaireResult | None = None,
    approved_by: str = "csv-import",
    tags=None,
) -> dict:
    """Promote filled CSV rows into the library (approve_one) and, if a run is
    given, into the run results. Returns counts + the updated result."""
    rows = list(csv.DictReader(Path(csv_path).open(encoding="utf-8")))
    imported = 0
    for row in rows:
        q = (row.get("question") or "").strip()
        a = (row.get("answer") or "").strip()
        if not q or not a:
            continue
        approve_one(q, a, qa_path, approved_by=approved_by, tags=row.get("category") or tags)
        imported += 1
        if result is not None:
            for r in result.results:
                if r.question_text.strip() == q and r.status == Status.NEEDS_REVIEW:
                    r.answer = a
                    r.status = Status.ANSWERED
                    r.review_reason = ReviewReason.NONE
                    r.citations = [Citation(source="csv-import (human)", snippet=a, faithful=True)]

    # Re-sync remaining flagged items against the now-updated library (Tier-1).
    resynced = 0
    if result is not None:
        library = AnswerLibrary.load(qa_path)
        for r in result.results:
            if r.status != Status.NEEDS_REVIEW:
                continue
            for e in library.entries:
                if lexical_similarity(r.question_text, e.question) >= AUTO_REUSE_THRESHOLD:
                    r.answer = e.answer
                    r.status = Status.ANSWERED
                    r.review_reason = ReviewReason.NONE
                    r.source_tier = 1
                    r.citations = [Citation(source="Answer Library", snippet=e.answer, faithful=True)]
                    resynced += 1
                    break

    return {"imported": imported, "resynced": resynced, "result": result}
