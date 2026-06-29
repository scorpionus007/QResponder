"""Core data models for QRESPONDER (pydantic v2).

These mirror §13.1 of the build spec exactly. They are the contract between the
extraction, retrieval, answering, and output layers — keep them stable, and
design new fields so later phases (faithfulness, attachments, write-back) slot
in without breaking callers.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnswerType(str, Enum):
    TEXT = "text"
    YES_NO = "yes_no"
    MULTI_SELECT = "multi_select"
    ATTACHMENT = "attachment"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(str, Enum):
    ANSWERED = "answered"
    NEEDS_REVIEW = "needs_review"


class ReviewReason(str, Enum):
    NONE = "none"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    FAITHFULNESS_FAIL = "faithfulness_fail"
    PARSE_ERROR = "parse_error"
    ATTACHMENT_UNRESOLVED = "attachment_unresolved"
    LIBRARY_CANDIDATE = "library_candidate"
    CONFLICT = "conflict"


class Question(BaseModel):
    id: str
    text: str
    answer_type: AnswerType = AnswerType.UNKNOWN
    section: str | None = None
    location_hint: str | None = None  # "Sheet1!C7" — the QUESTION's cell anchor
    # Where the ANSWER goes (distinct from location_hint), for write-back (C3).
    answer_location_hint: str | None = None
    # Populated when ambiguous; the extractor proposes readings, the human picks.
    interpretations: list[str] = Field(default_factory=list)
    ambiguous: bool = False


class Citation(BaseModel):
    source: str
    snippet: str
    # Set by the faithfulness check (Phase 1+); None means "not yet verified".
    faithful: bool | None = None


class InterpretationOption(BaseModel):
    """One reading of an ambiguous question with its own grounded draft (C1, §8)."""

    interpretation: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    status: Status = Status.NEEDS_REVIEW


class AnswerResult(BaseModel):
    question_id: str
    question_text: str
    answer: str
    answer_type: AnswerType
    citations: list[Citation] = Field(default_factory=list)
    confidence: Confidence
    status: Status
    review_reason: ReviewReason = ReviewReason.NONE
    missing_info: str | None = None
    attachment_path: str | None = None  # resolved attachment, if any (C2)
    attachment_candidates: list[str] = Field(default_factory=list)  # unresolved options (C2)
    source_tier: int | None = None  # 1=Library .. 3=Evidence
    # Interpretation candidates for ambiguous questions (C1).
    candidates: list[InterpretationOption] = Field(default_factory=list)
    # Explainable grounding/rerank score behind the confidence decision (S1/S2).
    grounding_score: float | None = None
    # Write-back anchors carried from the Question for format-perfect output (C3).
    location_hint: str | None = None
    answer_location_hint: str | None = None
    # Set when this answer contradicts another source (D1): a short description
    # of the conflicting source/answer the human must reconcile.
    conflict_with: str | None = None


class QuestionnaireResult(BaseModel):
    source_file: str
    results: list[AnswerResult] = Field(default_factory=list)
