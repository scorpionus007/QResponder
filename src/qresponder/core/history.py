"""Per-workspace answer history (Part G1).

A lightweight record of past submitted/approved answers ({question, answer,
date}) so a new run can be checked for drift against what was answered before
(see conflicts.detect_history_conflicts). The Answer Library already captures
approved answers; this additionally tracks point-in-time submissions over time.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..models import AnswerType, QuestionnaireResult, Status


class HistoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or []
        return [d for d in data if isinstance(d, dict) and d.get("question")]

    def append(self, result: QuestionnaireResult, date: str) -> int:
        """Append this run's answered text items to the history. `date` is passed
        in (callers stamp it) so this stays deterministic/testable."""
        entries = self.load()
        added = 0
        for r in result.results:
            if (r.status == Status.ANSWERED and r.answer_type != AnswerType.ATTACHMENT
                    and (r.answer or "").strip()):
                entries.append({"question": r.question_text, "answer": r.answer, "date": date})
                added += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(yaml.safe_dump(entries, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return added
