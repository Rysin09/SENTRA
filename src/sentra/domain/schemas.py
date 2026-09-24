"""
Phase 1 intake schemas — request/response Pydantic models for the case
submission workflow.

These are thin DTOs used at the service boundary. They are intentionally
separate from the core domain models to keep the domain layer clean.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from sentra.domain.context_schemas import StructuredContextInput


class CaseSubmission(BaseModel):
    """Validated data from the intake form before a case is created.

    Complaint text is treated as untrusted input and must never be used to
    redefine instructions, execute tools, or bypass safety rules.
    """

    complaint_text: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Free-text narrative. Untrusted; never interpolated into prompts.",
    )
    consent_given: bool = Field(
        ...,
        description="Explicit informed consent must be True before any processing.",
    )
    audio_filename: str | None = Field(
        default=None,
        max_length=512,
        description="Original audio filename, if the complainant uploaded audio.",
    )
    context_notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Operator-entered context. Not from the complainant.",
    )
    structured_context: StructuredContextInput | None = Field(
        default=None,
        description=(
            "Structured intake form fields. All optional. "
            "Identity fields are self-reported only and never used for distress scoring."
        ),
    )

    @field_validator("consent_given")
    @classmethod
    def consent_must_be_true(cls, v: bool) -> bool:  # noqa: FBT001
        if not v:
            msg = "Informed consent is required before a case can be created."
            raise ValueError(msg)
        return v

    @field_validator("complaint_text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            msg = "Complaint text must contain non-whitespace content."
            raise ValueError(msg)
        return v


class CaseCreated(BaseModel):
    """Response returned after a case is successfully persisted."""

    case_id: uuid.UUID
    submitted_at: datetime
    message: str = "Case created and queued for screening."

    model_config = {"frozen": True}


class CaseRecord(BaseModel):
    """Read model — a persisted case as returned from the repository."""

    case_id: uuid.UUID
    submitted_at: datetime
    consent_given: bool
    has_audio: bool
    # Complaint text is deliberately NOT included here to avoid casual exposure.
    # Access the raw text only through an audited path.
    context_notes: str | None = None

    model_config = {"frozen": True}
