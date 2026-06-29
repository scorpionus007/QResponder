"""Attachment resolution (Scrut L5, §9) — Phase 2.

Matches an attachment request ("provide your incident response plan") against
the evidence vault by similarity (local embedder if available, else lexical),
ranks candidates, and disambiguates close ones by version / recency. A clear
winner — above a minimum score AND beating the runner-up by a margin — is set as
`attachment_path` (ANSWERED, MEDIUM). Otherwise the top few are returned as
`attachment_candidates` for one-click human confirmation (NEEDS_REVIEW). We
never attach a file below the confidence margin without flagging.
"""

from __future__ import annotations

import logging

from ..kb.base import lexical_similarity
from ..kb.evidence import EvidenceIndex, EvidenceItem, _humanize
from ..models import AnswerResult, AnswerType, Confidence, Question, ReviewReason, Status

log = logging.getLogger("qresponder.attachments")

# Lexical similarity of a short request to a filename is inherently modest; the
# real guard against a wrong attachment is WINNER_MARGIN (top must clearly beat
# the runner-up), not a high absolute floor.
MIN_SCORE = 0.15          # below this, nothing is a real match
WINNER_MARGIN = 0.10      # top must beat runner-up by this to auto-resolve
# When there is no real runner-up, the margin is trivially satisfied, so a single
# weakly-related file would auto-attach. Require a higher absolute floor instead.
SOLO_MIN_SCORE = 0.30
TIE_EPSILON = 0.05        # within this, break ties by version/recency
N_CANDIDATES = 3


def _similarity(request: str, item: EvidenceItem, embedder=None) -> float:
    text = item.match_text()
    if embedder is not None:
        try:
            import numpy as np

            v = np.asarray(embedder.embed([request, text]), dtype=float)
            return float(v[0] @ v[1])
        except Exception:  # noqa: BLE001 - fall back to lexical
            pass
    # The filename is the strongest signal; don't let a long head-snippet dilute
    # it. Take the better of filename-only and filename+snippet similarity.
    name_sim = lexical_similarity(request, _humanize(item.filename))
    full_sim = lexical_similarity(request, text)
    return max(name_sim, full_sim)


def _tiebreak_key(scored_item):
    score, item = scored_item
    # Prefer higher version, then more recent date, then more specific (more) tags.
    return (item.version or -1, item.date or "", len(item.tags))


def resolve_attachment(
    question: Question,
    evidence: EvidenceIndex,
    config,
    scope_tags=None,
    embedder=None,
) -> AnswerResult:
    candidates = evidence.scoped(scope_tags)
    base = dict(
        question_id=question.id,
        question_text=question.text,
        answer_type=AnswerType.ATTACHMENT,
    )
    if not candidates:
        return AnswerResult(
            **base,
            answer="",
            citations=[],
            confidence=Confidence.LOW,
            status=Status.NEEDS_REVIEW,
            review_reason=ReviewReason.ATTACHMENT_UNRESOLVED,
            missing_info="No evidence files in scope to satisfy this attachment request.",
        )

    scored = sorted(
        ((_similarity(question.text, it, embedder), it) for it in candidates),
        key=lambda x: x[0],
        reverse=True,
    )
    top_score, top_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    # If the top two are effectively tied, let version/recency pick the winner.
    if len(scored) > 1 and (top_score - second_score) <= TIE_EPSILON:
        tied = [s for s in scored if top_score - s[0] <= TIE_EPSILON]
        top_score, top_item = max(tied, key=_tiebreak_key)
        remaining = [s for s in scored if s[1].filename != top_item.filename]
        second_score = remaining[0][0] if remaining else 0.0

    # A "real" runner-up is itself a plausible match; only then does the margin
    # guard meaningfully discriminate. With no real runner-up, fall back to an
    # absolute floor so a lone weak file is flagged, not auto-attached (SH2).
    has_real_runner_up = len(scored) > 1 and second_score >= MIN_SCORE
    if has_real_runner_up:
        clear_winner = top_score >= MIN_SCORE and (top_score - second_score) >= WINNER_MARGIN
    else:
        clear_winner = top_score >= SOLO_MIN_SCORE
    if clear_winner:
        return AnswerResult(
            **base,
            answer=top_item.filename,
            attachment_path=top_item.path,
            citations=[],
            confidence=Confidence.MEDIUM,  # resolved, but a human still confirms before submit
            status=Status.ANSWERED,
            review_reason=ReviewReason.NONE,
            source_tier=3,
        )

    top_files = [it.filename for _, it in scored[:N_CANDIDATES] if _ >= MIN_SCORE] or [
        it.filename for _, it in scored[:N_CANDIDATES]
    ]
    return AnswerResult(
        **base,
        answer="",
        attachment_candidates=top_files,
        citations=[],
        confidence=Confidence.LOW,
        status=Status.NEEDS_REVIEW,
        review_reason=ReviewReason.ATTACHMENT_UNRESOLVED,
        missing_info=f"Multiple/uncertain evidence matches — confirm one of: {', '.join(top_files)}.",
    )
