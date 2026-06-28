"""Format-perfect write-back into the ORIGINAL file (§15) — Phase 2.

Seam reserved now so callers and `Question.location_hint` are ready. When
implemented it will: load the original with openpyxl/python-docx, write each
answer into its location_hint anchor in a COPY, set values on the top-left cell
of merged ranges, reassign (not mutate) styles, and warn that openpyxl may drop
embedded images/charts on round-trip — falling back to the Phase-0 output file
when that risk exists.
"""

from __future__ import annotations

from ..models import QuestionnaireResult


def write_back(result: QuestionnaireResult, original_path: str, out_path: str) -> None:  # pragma: no cover
    raise NotImplementedError(
        "Format-perfect write-back is a Phase 2 feature. "
        "Use the Phase-0 answered.xlsx output for now."
    )
