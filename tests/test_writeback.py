"""Format-perfect write-back tests (C3, §15). Handles the openpyxl traps."""

from pathlib import Path

import openpyxl

from qresponder.models import (
    AnswerResult,
    AnswerType,
    Confidence,
    QuestionnaireResult,
    Status,
)
from qresponder.output.writeback import write_back


def _answered(qid, text, answer, anchor):
    return AnswerResult(
        question_id=qid,
        question_text=text,
        answer=answer,
        answer_type=AnswerType.YES_NO,
        confidence=Confidence.HIGH,
        status=Status.ANSWERED,
        answer_location_hint=anchor,
    )


def test_writeback_writes_to_merged_anchor_without_raising(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Q"
    ws["A1"] = "Question"
    ws["B1"] = "Response"
    ws["A2"] = "Do you encrypt data at rest?"
    ws.merge_cells("B2:C2")  # the answer cell is a merged range (anchor B2)
    orig = tmp_path / "q.xlsx"
    wb.save(orig)

    # Anchor points at C2 — a NON-anchor member of the merge. Write-back must
    # redirect to the top-left B2 and not raise.
    result = QuestionnaireResult(
        source_file=str(orig),
        results=[_answered("q1", "Do you encrypt data at rest?", "Yes, AES-256.", "Q!C2")],
    )
    info = write_back(result, str(orig), str(tmp_path / "out"))

    assert info["written"], info
    out_wb = openpyxl.load_workbook(info["written"])
    assert out_wb["Q"]["B2"].value == "Yes, AES-256."  # landed on the anchor

    # The ORIGINAL is never modified.
    assert openpyxl.load_workbook(orig)["Q"]["B2"].value is None
    assert Path(info["written"]).name == "q.answered.xlsx"


def test_writeback_preserves_style(tmp_path):
    from openpyxl.styles import Font

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Q"
    ws["A1"] = "Question"
    ws["A2"] = "Encrypt at rest?"
    ws["B2"].font = Font(bold=True)  # pre-existing style on the answer cell
    orig = tmp_path / "q.xlsx"
    wb.save(orig)

    result = QuestionnaireResult(
        source_file=str(orig),
        results=[_answered("q1", "Encrypt at rest?", "Yes.", "Q!B2")],
    )
    info = write_back(result, str(orig), str(tmp_path / "out"))
    out_ws = openpyxl.load_workbook(info["written"])["Q"]
    assert out_ws["B2"].value == "Yes."
    assert out_ws["B2"].font.bold is True  # style preserved (value-only write)


def test_writeback_falls_back_on_images(tmp_path):
    from openpyxl.drawing.image import Image
    from PIL import Image as PILImage

    img = tmp_path / "px.png"
    PILImage.new("RGB", (2, 2), (255, 0, 0)).save(img)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Q"
    ws["A2"] = "Encrypt at rest?"
    ws.add_image(Image(str(img)), "D1")
    orig = tmp_path / "q.xlsx"
    wb.save(orig)

    result = QuestionnaireResult(
        source_file=str(orig),
        results=[_answered("q1", "Encrypt at rest?", "Yes.", "Q!B2")],
    )
    info = write_back(result, str(orig), str(tmp_path / "out"))
    # Don't risk dropping the user's image — fall back, don't write.
    assert info["fallback"] is True
    assert info["written"] is None
    assert not (tmp_path / "out" / "q.answered.xlsx").exists()


def test_writeback_heuristic_response_column(tmp_path):
    """No explicit answer anchor -> find the 'Response' column in the question's row."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Q"
    ws["A1"] = "Question"
    ws["B1"] = "Response"
    ws["A2"] = "Encrypt at rest?"
    orig = tmp_path / "q.xlsx"
    wb.save(orig)

    r = _answered("q1", "Encrypt at rest?", "Yes, AES-256.", None)
    r.location_hint = "Q!A2"  # only the question cell is known
    result = QuestionnaireResult(source_file=str(orig), results=[r])
    info = write_back(result, str(orig), str(tmp_path / "out"))
    out_ws = openpyxl.load_workbook(info["written"])["Q"]
    assert out_ws["B2"].value == "Yes, AES-256."


def test_writeback_docx_paragraph(tmp_path):
    import docx

    d = docx.Document()
    d.add_paragraph("Do you encrypt at rest?")  # para[0]
    orig = tmp_path / "q.docx"
    d.save(orig)

    r = _answered("q1", "Do you encrypt at rest?", "Yes, AES-256.", "para[0]")
    r.answer_type = AnswerType.TEXT
    result = QuestionnaireResult(source_file=str(orig), results=[r])
    info = write_back(result, str(orig), str(tmp_path / "out"))
    out_doc = docx.Document(info["written"])
    assert "AES-256" in out_doc.paragraphs[0].text
