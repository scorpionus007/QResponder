"""Orchestration — the hard engineering (§5.2).

Per question, in order:
  1. Tier-1 Answer Library first (the authority). A strong, in-scope match is
     reused and marked source_tier=1 / HIGH confidence — no model call.
  2. Attachment-type questions are flagged NEEDS_REVIEW/attachment_unresolved
     (Phase 0 does not resolve files; Phase 2 does) — never sent to the text
     answerer where a model might fabricate.
  3. Everything else is batched and answered from the assembled, tag-scoped,
     cited KB context.

Original question order is preserved in the output.
"""

from __future__ import annotations

import logging

from ..config import Config
from ..kb.in_context import InContextKB
from ..kb.library import AnswerLibrary
from ..llm.base import LLMProvider
from ..models import (
    AnswerResult,
    AnswerType,
    Citation,
    Confidence,
    Question,
    ReviewReason,
    Status,
)
from .answer import answer_batch

log = logging.getLogger("qresponder.orchestrate")


def _library_result(q: Question, entry, score: float) -> AnswerResult:
    src = "Answer Library"
    if entry.approved_by:
        src += f" (approved by {entry.approved_by}, v{entry.version})"
    return AnswerResult(
        question_id=q.id,
        question_text=q.text,
        answer=entry.answer,
        answer_type=q.answer_type if q.answer_type != AnswerType.UNKNOWN else AnswerType.TEXT,
        citations=[Citation(source=src, snippet=entry.answer)],
        confidence=Confidence.HIGH,  # Tier-1 reuse (§11)
        status=Status.ANSWERED,
        review_reason=ReviewReason.NONE,
        source_tier=1,
    )


def _attachment_result(q: Question) -> AnswerResult:
    return AnswerResult(
        question_id=q.id,
        question_text=q.text,
        answer="",
        answer_type=AnswerType.ATTACHMENT,
        citations=[],
        confidence=Confidence.LOW,
        status=Status.NEEDS_REVIEW,
        review_reason=ReviewReason.ATTACHMENT_UNRESOLVED,
        missing_info="Attachment requested. Resolve the document manually (Phase 2 automates this).",
    )


def orchestrate(
    questions: list[Question],
    provider: LLMProvider,
    library: AnswerLibrary,
    kb: InContextKB,
    config: Config,
    scope_tags=None,
) -> list[AnswerResult]:
    results: dict[str, AnswerResult] = {}
    to_generate: list[Question] = []

    n_lib = 0
    n_attach = 0
    for q in questions:
        if q.answer_type == AnswerType.ATTACHMENT:
            results[q.id] = _attachment_result(q)
            n_attach += 1
            continue
        hit = library.match(q.text, scope_tags=scope_tags)
        if hit is not None:
            entry, score = hit
            results[q.id] = _library_result(q, entry, score)
            n_lib += 1
            continue
        to_generate.append(q)

    # Assemble the cited context once (Phase 0 in-context mode), tag-scoped.
    kb_context = kb.assemble_context(scope_tags=scope_tags, max_chars=config.max_kb_chars)

    batch_size = max(1, config.batch_size)
    n_gen = 0
    for i in range(0, len(to_generate), batch_size):
        batch = to_generate[i : i + batch_size]
        payload = [
            {
                "question_id": q.id,
                "question_text": q.text,
                "answer_type": q.answer_type.value,
            }
            for q in batch
        ]
        batch_results = answer_batch(provider, kb_context, payload)
        for r in batch_results:
            results[r.question_id] = r
            n_gen += 1

    log.info(
        "Orchestrated: %d tier-1 reuse, %d attachment-flagged, %d generated",
        n_lib,
        n_attach,
        n_gen,
    )
    # Preserve original order.
    ordered: list[AnswerResult] = []
    for q in questions:
        if q.id in results:
            ordered.append(results[q.id])
    return ordered
