"""Ingest loader tests — verify the IR captures layout signal (§6)."""

from pathlib import Path

import pytest

from qresponder.ingest.base import load_document, UnsupportedFileError

FIX = Path(__file__).parent / "fixtures"


def test_xlsx_captures_cells_merges_and_styles():
    doc = load_document(FIX / "sample.xlsx")
    assert doc.file_type == "xlsx"
    md = doc.render_markdown()

    # Questions are present, anchored by Sheet!Coord.
    assert "Security!B3" in md
    assert "Do you encrypt data at rest?" in md

    # The merged, colored, bold banner carries style flags.
    banner = next(e for e in doc.elements if e.location == "Security!A1")
    assert banner.style.get("merged") is True
    assert banner.style.get("bold") is True
    assert banner.style.get("fill")  # a fill color was captured

    # Blank response cells (column C body) are omitted.
    assert not any(e.location.startswith("Security!C") and int(e.location[-1]) >= 3
                   for e in doc.elements)


def test_docx_captures_paragraphs_and_headings():
    doc = load_document(FIX / "sample.docx")
    assert doc.file_type == "docx"
    md = doc.render_markdown()
    assert "multi-factor authentication" in md.lower()
    # A heading paragraph is flagged as a section.
    assert any(e.style.get("section") for e in doc.elements)


def test_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "f.txt"
    bad.write_text("hello")
    with pytest.raises(UnsupportedFileError):
        load_document(bad)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_document(FIX / "does_not_exist.xlsx")
