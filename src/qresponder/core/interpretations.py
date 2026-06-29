"""Ambiguity / interpretation surfacing (Scrut L3, §8) — Phase 2.

~1/3 of questionnaire items are ambiguous ("describe your encryption practices"
= at rest / in transit / backups / endpoints / DB). We never silently collapse
to one reading: for a question the extractor flagged ambiguous with >=2
interpretations, we draft one grounded answer per interpretation and surface them
all for the human to pick. Each draft is subject to the same guardrails as a
normal answer — snippet_supported citation filtering, no fabrication.
"""

from __future__ import annotations

import logging

from ..kb.base import snippet_supported
from ..llm.base import LLMProvider
from ..llm import prompts
from ..models import Citation, InterpretationOption, Status
from .parsing import parse_json_array

log = logging.getLogger("qresponder.interpretations")


def answer_interpretations(
    provider: LLMProvider,
    question_text: str,
    interpretations: list[str],
    kb_context: str,
) -> list[InterpretationOption]:
    """Draft one grounded answer per interpretation (single batched call)."""
    if not interpretations:
        return []
    user = prompts.build_interpretations_user(question_text, interpretations, kb_context)

    raw_items = None
    for _ in range(2):
        text = provider.complete(prompts.INTERPRETATIONS_SYSTEM, user, max_tokens=4096)
        try:
            raw_items = parse_json_array(text)
            break
        except ValueError:
            continue
    if raw_items is None:
        # Could not parse — surface the readings without drafts so the human
        # still sees the ambiguity rather than a fabricated single answer.
        return [InterpretationOption(interpretation=i, answer="", citations=[], status=Status.NEEDS_REVIEW)
                for i in interpretations]

    by_interp = {str(r.get("interpretation", "")).strip(): r for r in raw_items if isinstance(r, dict)}
    options: list[InterpretationOption] = []
    for interp in interpretations:
        raw = by_interp.get(interp.strip())
        if raw is None:
            options.append(InterpretationOption(interpretation=interp, answer="", citations=[], status=Status.NEEDS_REVIEW))
            continue
        citations = []
        for c in raw.get("citations") or []:
            if isinstance(c, dict) and c.get("snippet") and snippet_supported(str(c["snippet"]), kb_context):
                citations.append(Citation(source=str(c.get("source", "knowledge-base")), snippet=str(c["snippet"])))
        answer = str(raw.get("answer", "") or "").strip()
        status_raw = str(raw.get("status", "needs_review")).lower()
        # Guardrail: an "answered" interpretation with no supported citation is
        # not trustworthy — downgrade it (no fabrication).
        status = Status.ANSWERED if (status_raw == "answered" and citations) else Status.NEEDS_REVIEW
        if status != Status.ANSWERED:
            answer = answer if answer else ""
        options.append(InterpretationOption(interpretation=interp, answer=answer, citations=citations, status=status))
    return options
