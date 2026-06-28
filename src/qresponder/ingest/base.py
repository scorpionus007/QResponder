"""Ingestion dispatch: file -> layout-aware IR Document.

A pluggable `PARSER_BACKEND` seam is reserved (§6) so a neural/VLM PDF parser
(Marker/Docling-style) can be swapped in later without touching callers. Not
implemented in Phase 0.
"""

from __future__ import annotations

from pathlib import Path

from .ir import Document


class UnsupportedFileError(ValueError):
    """Raised when a file extension has no loader."""


def load_document(path: str | Path) -> Document:
    """Load any supported questionnaire file into a layout-aware IR Document."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Questionnaire file not found: {p}")

    ext = p.suffix.lower()
    if ext in {".xlsx", ".xlsm"}:
        from .xlsx import load_xlsx

        return load_xlsx(p)
    if ext == ".docx":
        from .docx import load_docx

        return load_docx(p)
    if ext == ".pdf":
        from .pdf import load_pdf

        return load_pdf(p)

    raise UnsupportedFileError(
        f"Unsupported questionnaire format '{ext}'. "
        "Supported: .xlsx/.xlsm, .docx, .pdf"
    )
