"""
Shared enumerations used across the SENTRA domain.

These values are stable reference types; any change here may require
a corresponding Alembic migration for database-stored columns.
"""

from __future__ import annotations

from enum import Enum


class OperationalCategory(str, Enum):
    """Operational screening priority categories.

    These categories represent operational review priority ONLY.
    They are not medical diagnoses, legal determinations, or
    psychiatric classifications.
    """

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ModalityType(str, Enum):
    """Input modalities that SENTRA can process."""

    TEXT = "TEXT"
    AUDIO = "AUDIO"
    CONTEXT = "CONTEXT"


class ModalityQuality(str, Enum):
    """Subjective quality rating of a processed modality."""

    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    NOT_PROVIDED = "NOT_PROVIDED"


class ReviewStatus(str, Enum):
    """Human review workflow status."""

    PENDING = "PENDING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    OVERRIDDEN = "OVERRIDDEN"


class AuditEventType(str, Enum):
    """Categories of audit-trail events.

    Audit events must NOT contain raw sensitive complaint content.
    """

    CASE_CREATED = "CASE_CREATED"
    ASSESSMENT_GENERATED = "ASSESSMENT_GENERATED"
    SAFETY_FLAG_RAISED = "SAFETY_FLAG_RAISED"
    REVIEW_STARTED = "REVIEW_STARTED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"
    SYSTEM_ERROR = "SYSTEM_ERROR"
