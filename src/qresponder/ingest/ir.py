"""Layout-Aware Intermediate Representation (IR).

§6: the model must see *layout signal* — cell coordinates, merged ranges,
fill colors, bold — because color and merges carry meaning in real
questionnaires. Loaders emit a `Document` of `Element`s; `render_markdown()`
produces the compact, layout-preserving text the LLM extractor reads.

We deliberately do NOT convert spreadsheets to PDF/image and OCR them (that
reorders columns and drops style semantics). Native loaders only.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Element(BaseModel):
    """One atomic piece of the document with its location and style signals."""

    kind: str  # "cell" | "paragraph" | "table_cell" | "pdf_line" | "pdf_field"
    location: str  # write-back anchor, e.g. "Sheet1!C7", "para[12]", "p1"
    text: str
    style: dict = Field(default_factory=dict)  # bold, fill, merged, etc.


class Document(BaseModel):
    """A normalized, layout-aware view of an ingested file."""

    source_file: str
    file_type: str  # "xlsx" | "docx" | "pdf"
    elements: list[Element] = Field(default_factory=list)

    def render_markdown(self) -> str:
        """Render a compact, layout-preserving text block for the extractor.

        Each line carries its location anchor and any meaningful style flags so
        the LLM can reason about what is a question vs. a header/instruction.
        """
        lines: list[str] = [
            f"# Document: {self.source_file} (type: {self.file_type})",
            "",
        ]
        for el in self.elements:
            flags = _format_style(el.style)
            flag_str = f"  [{flags}]" if flags else ""
            text = el.text.replace("\r", " ").strip()
            if not text:
                continue
            lines.append(f"- {el.location} = {text}{flag_str}")
        return "\n".join(lines)


def _format_style(style: dict) -> str:
    parts: list[str] = []
    if style.get("bold"):
        parts.append("bold")
    if style.get("merged"):
        parts.append("merged")
    fill = style.get("fill")
    if fill:
        parts.append(f"fill={fill}")
    section = style.get("section")
    if section:
        parts.append("section")
    return ",".join(parts)
