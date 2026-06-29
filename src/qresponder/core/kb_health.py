"""Answer Library health check (Phase 7, Part B).

The flywheel grows the library over time; this scans it against ITSELF for:
  (a) internal contradictions — approved entries for similar questions whose
      answers contradict (reuses conflicts.py heuristics + the same floor;
      optional conservative judge for nuance), and
  (b) near-duplicates — entries above the auto-reuse band that should be merged.

Read-only / non-destructive by default — it reports; a human decides. An optional
merge_duplicates re-approves (version-bumps) the canonical via approve_one, but
NEVER auto-deletes anything. Compares answers, not the self-citations.
"""

from __future__ import annotations

import logging

from ..kb.base import lexical_similarity
from ..kb.library import AUTO_REUSE_THRESHOLD, AnswerLibrary
from ..llm import prompts
from .conflicts import _heuristic_conflict, _short
from .parsing import parse_json_array

log = logging.getLogger("qresponder.kb_health")


def check_library(qa_path, provider=None, config=None) -> dict:
    lib = AnswerLibrary.load(qa_path)
    entries = lib.entries
    floor = getattr(config, "conflict_similarity_floor", 0.4) if config else 0.4
    use_judge = getattr(config, "conflict_use_judge", True) if config else False

    contradictions: list[dict] = []
    duplicates: list[dict] = []
    judge_queue: list[dict] = []
    pair_meta: dict[str, tuple] = {}

    for i in range(len(entries)):
        for j in range(i + 1, len(entries)):
            a, b = entries[i], entries[j]
            sim = lexical_similarity(a.question, b.question)
            if sim < floor:
                continue
            if _heuristic_conflict(a.answer, b.answer):
                contradictions.append(_pair(i, j, a, b, sim))
            elif sim >= AUTO_REUSE_THRESHOLD:
                duplicates.append(_pair(i, j, a, b, sim))
            elif use_judge and provider is not None:
                pid = f"k{len(pair_meta)}"
                judge_queue.append({"id": pid, "a_question": a.question, "a_answer": a.answer,
                                    "b_question": b.question, "b_answer": b.answer})
                pair_meta[pid] = (i, j, a, b, sim)

    if judge_queue and provider is not None:
        try:
            text = provider.complete(prompts.CONFLICT_SYSTEM, prompts.build_conflict_user(judge_queue), max_tokens=2048)
            for v in parse_json_array(text):
                if isinstance(v, dict) and v.get("conflict") and str(v.get("id")) in pair_meta:
                    i, j, a, b, sim = pair_meta[str(v["id"])]
                    contradictions.append(_pair(i, j, a, b, sim))
        except Exception as exc:  # noqa: BLE001
            log.warning("kb-check judge failed (%s); heuristics only.", exc)

    return {
        "n_entries": len(entries),
        "contradictions": contradictions,
        "duplicates": duplicates,
        "clean": not contradictions and not duplicates,
    }


def _pair(i, j, a, b, sim) -> dict:
    return {
        "a_index": i, "b_index": j, "similarity": round(sim, 3),
        "question_a": a.question, "answer_a": _short(a.answer),
        "question_b": b.question, "answer_b": _short(b.answer),
    }


def merge_duplicates(qa_path, config=None) -> dict:
    """Version-bump the canonical of each duplicate pair via approve_one. Never
    deletes (the human still reviews). Returns the count of merges performed."""
    from .flywheel import approve_one

    report = check_library(qa_path, config=config)
    merged = 0
    for dup in report["duplicates"]:
        lib = AnswerLibrary.load(qa_path)
        if dup["a_index"] < len(lib.entries):
            e = lib.entries[dup["a_index"]]
            approve_one(e.question, e.answer, qa_path, approved_by=e.approved_by, tags=e.tags)
            merged += 1
    return {"merged": merged, "duplicates_found": len(report["duplicates"])}
