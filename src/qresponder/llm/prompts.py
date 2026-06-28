"""The two core prompts (§14) plus the markers the MockProvider keys off.

Keeping the structure explicit (clear section markers) makes model-agnostic
strict-JSON parsing reliable on weak local models, and lets the deterministic
MockProvider locate the KB context and questions without a real model.
"""

from __future__ import annotations

import json

# Markers embedded in the answer-call user message. Stable strings so the
# defensive parser and MockProvider can split context from questions.
KB_CONTEXT_MARKER = "=== KNOWLEDGE BASE CONTEXT ==="
QUESTIONS_MARKER = "=== QUESTIONS (JSON) ==="

# --- Call #1: extraction -----------------------------------------------------

EXTRACT_SYSTEM = (
    "You extract questions from vendor security questionnaires. Use the layout "
    "(cell coordinates, merges, colors, sections) to decide what is a question "
    "vs. an instruction or header, and what answer each expects. "
    "Return ONLY a JSON array, no prose, no code fences. "
    "Each item must be an object with keys: "
    "id (string), question_text (string), "
    "answer_type (one of: text, yes_no, multi_select, attachment), "
    "section (string or null), location_hint (string or null), "
    "ambiguous (boolean), interpretations (array of strings)."
)


def build_extract_user(layout_ir: str) -> str:
    return (
        "Here is the layout-aware representation of the questionnaire. Extract "
        "every question.\n\n" + layout_ir
    )


# --- Call #2: answering ------------------------------------------------------

ANSWER_SYSTEM = (
    "Answer STRICTLY from the provided knowledge base context. Prefer APPROVED "
    "ANSWERS when a question matches. Never invent certifications, controls, "
    "audits, or compliance status. If the knowledge base does not support an "
    "answer, set status to 'needs_review', set review_reason to 'unsupported', "
    "and state what is missing in missing_info. Constrain each answer to its "
    "answer_type. Every 'answered' item MUST include at least one citation with "
    "the exact source and a verbatim snippet from the context. "
    "Return ONLY a JSON array, no prose, no code fences. Each item must be an "
    "object with keys: question_id, answer, answer_type, "
    "citations (array of {source, snippet}), confidence (high|medium|low), "
    "status (answered|needs_review), "
    "review_reason (none|ambiguous|unsupported|faithfulness_fail|parse_error|attachment_unresolved), "
    "missing_info (string or null), source_tier (integer or null)."
)


def build_answer_user(kb_context: str, questions: list[dict]) -> str:
    return (
        f"{KB_CONTEXT_MARKER}\n{kb_context}\n\n"
        f"{QUESTIONS_MARKER}\n{json.dumps(questions, ensure_ascii=False, indent=2)}"
    )
