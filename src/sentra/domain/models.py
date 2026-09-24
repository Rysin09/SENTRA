"""
Core Pydantic domain models for SENTRA.

These schemas define the immutable value objects and aggregates that flow
through the screening pipeline. They are designed for strict validation
and must not carry ORM-specific concerns.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from sentra.context.india_context_layer import IndiaContextAssessment  # noqa: E402

# Imported at module level to resolve Pydantic v2 forward references.
# These are placed after domain.enums to avoid circular imports
# (context_schemas and india_context_layer do not import from models.py).
from sentra.domain.context_schemas import StructuredContextInput  # noqa: E402
from sentra.domain.enums import (
    AuditEventType,
    ModalityQuality,
    ModalityType,
    OperationalCategory,
    ReviewStatus,
)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


# ── Input models ─────────────────────────────────────────────────────────────


class CaseInput(BaseModel):
    """Raw, validated input submitted for a new case.

    Text is treated as untrusted user data and must never be used
    to redefine instructions or bypass safety rules.
    """

    case_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    submitted_at: datetime = Field(default_factory=_utc_now)
    complaint_text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="The complainant's free-text narrative. Treated as untrusted.",
    )
    consent_given: bool = Field(
        ...,
        description="Explicit consent must be recorded before processing.",
    )
    audio_filename: str | None = Field(
        default=None,
        description="Original filename of the uploaded audio, if any.",
    )
    context_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Operator-entered context (e.g., channel, language preference).",
    )
    structured_context: StructuredContextInput | None = Field(
        default=None,
        description=(
            "Structured intake form fields. All fields are optional. "
            "Identity fields (social_identity_context, minority_community_context) "
            "are self-reported only and NEVER used to adjust distress/vulnerability scores."
        ),
    )

    @field_validator("consent_given")
    @classmethod
    def consent_must_be_given(cls, v: bool) -> bool:  # noqa: FBT001
        if not v:
            msg = "Consent must be given before processing can begin."
            raise ValueError(msg)
        return v


# ── Modality models ───────────────────────────────────────────────────────────


class ModalityStatus(BaseModel):
    """Tracks the availability and quality of each input modality."""

    modality: ModalityType
    quality: ModalityQuality = ModalityQuality.NOT_PROVIDED
    available: bool = False
    notes: str | None = None


class AudioMetadata(BaseModel):
    """Metadata about an uploaded audio file (no raw audio bytes stored here)."""

    filename: str
    duration_seconds: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    format: str | None = None
    size_bytes: int | None = None


# ── Assessment models ─────────────────────────────────────────────────────────


class AssessmentDimension(BaseModel):
    """A single operational assessment dimension.

    Scores are 0.0–1.0.  These are screening indicators, NOT diagnoses.
    """

    name: str = Field(..., description="Dimension identifier, e.g. 'acute_distress'.")
    score: float = Field(..., ge=0.0, le=1.0)
    label: str | None = Field(
        default=None,
        description="Human-readable label derived from score.",
    )
    supporting_indicators: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)


class SafetyFlag(BaseModel):
    """A flag raised by a deterministic safety rule."""

    rule_id: str
    description: str
    forces_human_review: bool = True


class AssessmentResult(BaseModel):
    """The complete output of the SENTRA screening pipeline for one case.

    Every field is required. If processing fails, ``operational_category``
    must be set to ``INSUFFICIENT_DATA`` and ``human_review_required``
    must be True.
    """

    case_id: uuid.UUID
    assessed_at: datetime = Field(default_factory=_utc_now)
    pipeline_version: str = Field(default="0.1.0")

    modalities_used: list[ModalityStatus] = Field(default_factory=list)

    dimensions: list[AssessmentDimension] = Field(default_factory=list)

    operational_category: OperationalCategory = OperationalCategory.INSUFFICIENT_DATA
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    explanation: str = Field(
        default="Insufficient data for reliable screening — Human Review Required."
    )
    safety_flags: list[SafetyFlag] = Field(default_factory=list)
    human_review_required: bool = True

    # ── LLM audit metadata ────────────────────────────────────────────────────
    # Carries provider/model/schema_version from the pipeline to the repository
    # serializer. Stored inside dimensions_json under a reserved "_meta" key.
    # Never contains API keys, secrets, or raw complaint text.
    extra_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Non-sensitive pipeline metadata for auditability. "
            "Stored in dimensions_json._meta. Never contains secrets."
        ),
    )
    india_context: IndiaContextAssessment | None = Field(
        default=None,
        description=(
            "Deterministic India-specific legal/contextual relevance assessment. "
            "Advisory only — never a legal determination. Requires human review."
        ),
    )

    @model_validator(mode="after")
    def insufficient_data_requires_human_review(self) -> AssessmentResult:
        if self.operational_category == OperationalCategory.INSUFFICIENT_DATA:
            self.human_review_required = True
        return self

    @property
    def has_safety_flags(self) -> bool:
        return len(self.safety_flags) > 0


# ── Human review models ───────────────────────────────────────────────────────


class HumanReview(BaseModel):
    """A reviewer's decision recorded after inspecting an assessment."""

    review_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    case_id: uuid.UUID
    reviewer_id: str = Field(..., description="Authenticated reviewer identifier.")
    reviewed_at: datetime = Field(default_factory=_utc_now)
    status: ReviewStatus = ReviewStatus.COMPLETED

    ai_category: OperationalCategory
    reviewer_category: OperationalCategory
    overridden: bool = False
    reviewer_note: str | None = Field(default=None, max_length=2000)


# ── Audit model ───────────────────────────────────────────────────────────────


class AuditEvent(BaseModel):
    """An immutable audit trail entry.

    Must NOT contain raw sensitive complaint content.
    """

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    occurred_at: datetime = Field(default_factory=_utc_now)
    event_type: AuditEventType
    case_id: uuid.UUID | None = None
    actor_id: str | None = Field(default=None, description="Reviewer or system ID.")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-sensitive structured event metadata.",
    )
