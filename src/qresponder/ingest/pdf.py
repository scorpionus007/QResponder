"""PDF loader (§6, Stage A).

Uses pdfplumber for text lines and tables, and captures form-field/widget
annotations where present (radio/checkbox/text fields). For scanned or complex
PDFs a neural parser can later be plugged in behind `base.PARSER_BACKEND`; not
required in Phase 0.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .ir import Document, Element


def load_pdf(path: str | Path) -> Document:
    p = Path(path)
    elements: list[Element] = []

    with pdfplumber.open(str(p)) as pdf:
        for pi, page in enumerate(pdf.pages, start=1):
            # Tables first, so their cells carry an explicit table anchor.
            try:
                tables = page.extract_tables() or []
            except Exception:
                tables = []
            for ti, table in enumerate(tables):
                for ri, prow in enumerate(table):
                    for ci, cellval in enumerate(prow):
                        text = (cellval or "").strip()
                        if not text:
                            continue
                        elements.append(
                            Element(
                                kind="table_cell",
                                location=f"p{pi}.tbl{ti}.r{ri}.c{ci}",
                                text=text,
                                style={"table": True},
                            )
                        )

            # Then plain text lines.
            text = page.extract_text() or ""
            for li, line in enumerate(text.splitlines()):
                line = line.strip()
                if not line:
                    continue
                elements.append(
                    Element(
                        kind="pdf_line",
                        location=f"p{pi}.L{li}",
                        text=line,
                        style={},
                    )
                )

            # Form-field / widget annotations where present.
            for ai, annot in enumerate(page.annots or []):
                data = annot.get("data", {}) if isinstance(annot, dict) else {}
                field_name = annot.get("title") or data.get("T")
                if not field_name:
                    continue
                elements.append(
                    Element(
                        kind="pdf_field",
                        location=f"p{pi}.field{ai}",
                        text=str(field_name),
                        style={"form_field": True},
                    )
                )

    return Document(source_file=str(p), file_type="pdf", elements=elements)
