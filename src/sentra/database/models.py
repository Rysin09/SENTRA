"""
SQLAlchemy ORM models for SENTRA.

These are the database-persisted representations of domain entities.
Domain Pydantic schemas live in ``sentra.domain.models``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from sentra.database.base import Base


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


class CaseRecord(Base):
    """Persisted case submission."""

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Raw complaint text is stored; access must be audit-logged.
    complaint_text: Mapped[str] = mapped_column(Text, nullable=False)
    audio_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    context_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured intake context (JSON blob). Nullable for backward compat.
    # Never contains raw complaint text. Identity fields stored here but
    # NOT exposed to the LLM — only used by the deterministic IndiaContextLayer.
    context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)


class AssessmentRecord(Base):
    """Persisted screening assessment result."""

    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    operational_category: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # JSON blobs for structured data (migrated to columns as schema stabilises)
    dimensions_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    modalities_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    safety_flags_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # India-specific legal/contextual relevance (nullable for backward compat)
    india_context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)


class ReviewRecord(Base):
    """Persisted human review decision."""

    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(256), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ai_category: Mapped[str] = mapped_column(String(32), nullable=False)
    reviewer_category: Mapped[str] = mapped_column(String(32), nullable=False)
    overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditEventRecord(Base):
    """Immutable audit trail entry.

    Must NOT store raw sensitive complaint content.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    details_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
