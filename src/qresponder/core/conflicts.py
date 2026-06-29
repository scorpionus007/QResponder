"""Cross-source conflict detection (Scrut L2, §5.2) — Phase 3.

Contradictory answers are the most common reason a questionnaire gets kicked
back. We already ground, cite, and faithfulness-check; this catches when two
answers DISAGREE. Each generated ANSWERED result is compared against:
  (a) the Answer Library (Tier-1 approved answers), and
  (b) the other answered results in this run,
but only for semantically-similar questions (a similarity floor — never compare
unrelated questions).

Contradiction is decided cheaply first (opposite yes/no; differing values for the
same control — TLS/AES versions, retention periods), then, for nuanced pairs, an
optional batched LLM-judge (config-gated, provider-agnostic, local-safe).

Conservative by design — only clear contradictions are flagged, to avoid
review-queue noise. Conflicts are NEVER auto-resolved: both sides are surfaced.
A generated answer contradicting an approved Tier-1 answer is always flagged
(the approved answer is never silently overridden).
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from ..kb.base import lexical_similarity
from ..llm import prompts
from ..llm.base import LLMProvider
from ..models import AnswerResult, AnswerType, Confidence, ReviewReason, Status
from .parsing import parse_json_array

log = logging.getLogger("qresponder.conflicts")

_SUMMARY_CHARS = 140


def _yesno(answer: str) -> str | None:
    t = answer.strip().lower()
    if t.startswith("yes"):
        return "yes"
    if t.startswith(("no.", "no ", "no,")) or t == "no":
        return "no"
    return None


def _values(text: str) -> dict[str, set[str]]:
    t = text.lower()
    d: dict[str, set[str]] = defaultdict(set)
    for m in re.finditer(r"tls\s*v?(\d+(?:\.\d+)?)", t):
        d["tls"].add(m.group(1))
    for m in re.finditer(r"aes[-\s]?(\d{2,3})", t):
        d["aes"].add(m.group(1))
    for m in re.finditer(r"(\d+)\s*(day|week|month|year)s?", t):
        d[m.group(2)].add(m.group(1))
    return d


def _value_conflict(a: str, b: str) -> bool:
    da, db = _values(a), _values(b)
    for key in set(da) & set(db):
        if da[key] and db[key] and da[key].isdisjoint(db[key]):
            return True
    return False


def _heuristic_conflict(a: str, b: str) -> bool:
    ya, yb = _yesno(a), _yesno(b)
    if ya and yb and ya != yb:
        return True
    return _value_conflict(a, b)


def _summary(question: str, answer: str, source: str) -> str:
    ans = answer.strip()
    if len(ans) > _SUMMARY_CHARS:
        ans = ans[: _SUMMARY_CHARS - 1] + "…"
    return f"{source}: \"{ans}\""


def _flag(result: AnswerResult, desc: str) -> None:
    # Don't clobber an already-recorded conflict; keep the first.
    if result.review_reason == ReviewReason.CONFLICT and result.conflict_with:
        return
    result.status = Status.NEEDS_REVIEW
    result.review_reason = ReviewReason.CONFLICT
    result.confidence = Confidence.LOW
    result.conflict_with = desc
    if not result.missing_info:
        result.missing_info = "Contradicts another source — reconcile before using."


def detect_conflicts(
    results: list[AnswerResult],
    library,
    provider: LLMProvider,
    config,
) -> list[AnswerResult]:
    """Flag contradictory answered results in place. Returns the same list."""
    if not getattr(config, "detect_conflicts", True):
        return results

    floor = getattr(config, "conflict_similarity_floor", 0.5)
    use_judge = getattr(config, "conflict_use_judge", True)

    # Answered text results in this run (attachments excluded — they're files).
    run = [
        r
        for r in results
        if r.status == Status.ANSWERED and r.answer_type != AnswerType.ATTACHMENT and r.answer.strip()
    ]

    # (result_to_flag, description) pairs to apply after judging.
    to_flag: list[tuple[AnswerResult, str]] = []
    judge_queue: list[dict] = []  # {id, targets:[...], a_*, b_*}
    pair_meta: dict[str, tuple] = {}

    def queue_judge(a_obj, b_obj, flag_objs):
        pid = f"p{len(pair_meta)}"
        a_q = a_obj.question_text
        a_a = a_obj.answer
        b_q = getattr(b_obj, "question_text", None) or getattr(b_obj, "question", "")
        b_a = getattr(b_obj, "answer", "")
        b_src = getattr(b_obj, "source_label", "Answer Library")
        judge_queue.append(
            {"id": pid, "a_question": a_q, "a_answer": a_a, "b_question": b_q, "b_answer": b_a}
        )
        pair_meta[pid] = (flag_objs, b_q, b_a, b_src)

    # (b) run-vs-run pairs.
    for i in range(len(run)):
        for j in range(i + 1, len(run)):
            a, b = run[i], run[j]
            if lexical_similarity(a.question_text, b.question_text) < floor:
                continue
            # Only flag non-Tier-1 results; never flag the approved answer.
            flaggable = [x for x in (a, b) if x.source_tier != 1]
            if not flaggable:
                continue
            if _heuristic_conflict(a.answer, b.answer):
                if a.source_tier != 1:
                    to_flag.append((a, _summary(b.question_text, b.answer, "another answer")))
                if b.source_tier != 1:
                    to_flag.append((b, _summary(a.question_text, a.answer, "another answer")))
            elif use_judge:
                queue_judge(a, b, flaggable)

    # (a) run-vs-library pairs (flag only the generated run answer).
    entries = getattr(library, "entries", []) if library is not None else []
    for a in run:
        if a.source_tier == 1:
            continue  # a reused approved answer can't contradict the library
        for entry in entries:
            if lexical_similarity(a.question_text, entry.question) < floor:
                continue
            if _heuristic_conflict(a.answer, entry.answer):
                to_flag.append((a, _summary(entry.question, entry.answer, "Answer Library")))
            elif use_judge:
                queue_judge(a, entry, [a])

    # Nuanced pairs -> one batched judge call.
    if judge_queue:
        try:
            text = provider.complete(
                prompts.CONFLICT_SYSTEM, prompts.build_conflict_user(judge_queue), max_tokens=2048
            )
            for v in parse_json_array(text):
                if not isinstance(v, dict) or not v.get("conflict"):
                    continue
                meta = pair_meta.get(str(v.get("id")))
                if not meta:
                    continue
                flag_objs, b_q, b_a, b_src = meta
                for obj in flag_objs:
                    to_flag.append((obj, _summary(b_q, b_a, b_src)))
        except Exception as exc:  # noqa: BLE001 - judge failure shouldn't crash a run
            log.warning("Conflict judge failed (%s); using heuristic results only.", exc)

    for result, desc in to_flag:
        _flag(result, desc)

    n = len({id(r) for r, _ in to_flag})
    if n:
        log.info("Conflict detection flagged %d answer(s).", n)
    return results
