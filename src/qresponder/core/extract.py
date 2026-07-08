"""Question extraction — LLM call #1 (§6 Stage B, §14).

The model (not code) decides what is a question vs. an instruction/header and
what answer type each expects, reading the layout-aware IR. Output is validated
to `Question` objects with a defensive parse + one retry.
"""

from __future__ import annotations

import logging

from ..ingest.ir import Document
from ..llm.base import LLMProvider
from ..llm import prompts
from ..models import AnswerType, Question
from .parsing import parse_json_array

log = logging.getLogger("qresponder.extract")

_VALID_TYPES = {t.value for t in AnswerType}


def _coerce_question(raw: dict, index: int) -> Question | None:
    text = (raw.get("question_text") or raw.get("text") or "").strip()
    if not text:
        return None
    atype = str(raw.get("answer_type", "unknown")).strip().lower()
    if atype not in _VALID_TYPES:
        atype = "unknown"
    interps = raw.get("interpretations") or []
    if not isinstance(interps, list):
        interps = []
    return Question(
        id=str(raw.get("id") or f"q{index}"),
        text=text,
        answer_type=AnswerType(atype),
        section=(raw.get("section") or None),
        location_hint=(raw.get("location_hint") or None),
        answer_location_hint=(raw.get("answer_location_hint") or None),
        ambiguous=bool(raw.get("ambiguous", False)),
        interpretations=[str(x) for x in interps],
    )


# Elements per extraction call. Chunking bounds each call's OUTPUT so the JSON
# array can never overflow a provider's token budget (incl. "thinking" tokens) —
# extraction is correct at ANY questionnaire size, on any model.
_ELEMENTS_PER_CHUNK = 60
_EXTRACT_MAX_TOKENS = 8192


def _extract_chunk(doc: Document, elements: list, provider: LLMProvider) -> list[dict]:
    """Run the LLM extractor over a bounded slice of the document. Returns raw dicts.
    A parse failure on one chunk salvages what it can and doesn't sink the rest."""
    sub = Document(source_file=doc.source_file, file_type=doc.file_type, elements=elements)
    user = prompts.build_extract_user(sub.render_markdown())
    last_err: Exception | None = None
    for attempt in range(2):
        text = provider.complete(prompts.EXTRACT_SYSTEM, user, max_tokens=_EXTRACT_MAX_TOKENS)
        try:
            return [r for r in parse_json_array(text) if isinstance(r, dict)]
        except ValueError as exc:
            last_err = exc
            log.warning("Extraction parse failed (attempt %d): %s", attempt + 1, exc)
    raise ValueError(f"Failed to extract questions after 2 attempts: {last_err}")


def extract_questions(doc: Document, provider: LLMProvider) -> list[Question]:
    """Extract questions from a document's IR. The document is processed in bounded
    chunks so no single model call can be truncated, regardless of questionnaire size;
    results are merged and de-duplicated across chunks."""
    elements = [e for e in doc.elements if (e.text or "").strip()]

    raw_items: list[dict] = []
    if len(elements) <= _ELEMENTS_PER_CHUNK:
        raw_items = _extract_chunk(doc, elements, provider)
    else:
        n_chunks = (len(elements) + _ELEMENTS_PER_CHUNK - 1) // _ELEMENTS_PER_CHUNK
        log.info("Large questionnaire (%d elements) — extracting in %d chunk(s).",
                 len(elements), n_chunks)
        for start in range(0, len(elements), _ELEMENTS_PER_CHUNK):
            chunk = elements[start : start + _ELEMENTS_PER_CHUNK]
            try:
                raw_items.extend(_extract_chunk(doc, chunk, provider))
            except ValueError as exc:  # one bad chunk shouldn't drop the whole file
                log.warning("Chunk starting at element %d failed to parse: %s", start, exc)

    # Coerce + de-duplicate across chunks (by answer/location anchor, else question text).
    questions: list[Question] = []
    seen_keys: set[str] = set()
    for i, raw in enumerate(raw_items, start=1):
        q = _coerce_question(raw, i)
        if q is None:
            continue
        key = (q.location_hint or q.answer_location_hint or q.text).strip().lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        questions.append(q)

    # GUARDRAIL (F3): results are keyed by question id downstream; a model that
    # emits duplicate ids would silently drop questions. Make ids unique,
    # preserving model ids where unique and suffixing on collision.
    seen: set[str] = set()
    for q in questions:
        base = q.id
        n = 2
        while q.id in seen:
            q.id = f"{base}-{n}"
            n += 1
        seen.add(q.id)

    log.info("Extracted %d question(s)", len(questions))
    return questions
