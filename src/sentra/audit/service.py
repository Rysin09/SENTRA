"""
Audit service — records key state transitions in the audit trail.

Wraps AuditRepository with domain-level helper methods so callers
do not need to know the audit schema details.

Rule 15: Record actor, timestamp, action, case_id, and status
         WITHOUT sensitive complaint content.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from sentra.domain.enums import AuditEventType
from sentra.repositories.audit_repository import AuditRepository


class AuditService:
    """Domain-level façade over AuditRepository."""

    def __init__(self, session: Session) -> None:
        self._repo = AuditRepository(session)

    def case_created(self, case_id: uuid.UUID, *, has_audio: bool) -> None:
        """Record that a new case was created.

        Args:
            case_id: The new case UUID.
            has_audio: Whether an audio file was attached (metadata only).
        """
        self._repo.record(
            AuditEventType.CASE_CREATED,
            case_id=case_id,
            actor_id="system:intake",
            details={"has_audio": has_audio},
        )

    def system_error(
        self,
        *,
        case_id: uuid.UUID | None = None,
        error_type: str,
        message: str,
    ) -> None:
        """Record a system-level error without exposing sensitive content.

        Args:
            case_id: Associated case, if known.
            error_type: A short error category string, e.g. 'db_error'.
            message: A non-sensitive description of the error.
        """
        self._repo.record(
            AuditEventType.SYSTEM_ERROR,
            case_id=case_id,
            actor_id="system",
            details={"error_type": error_type, "message": message},
        )

    def assessment_generated(
        self,
        case_id: uuid.UUID,
        *,
        pipeline_version: str,
        operational_category: str,
        confidence: float,
        human_review_required: bool,
    ) -> None:
        """Record that an AI screening assessment was generated.

        Args:
            case_id: The assessed case UUID.
            pipeline_version: The pipeline version string (e.g. '0.2.0').
            operational_category: The derived category (e.g. 'HIGH').
            confidence: The estimated confidence score (0.0–1.0).
            human_review_required: Whether human review is required.

        Notes:
            MUST NOT include complaint text or dimension indicator details
            that could expose sensitive content. Only metadata is recorded.
        """
        self._repo.record(
            AuditEventType.ASSESSMENT_GENERATED,
            case_id=case_id,
            actor_id="system:nlp_pipeline",
            details={
                "pipeline_version": pipeline_version,
                "operational_category": operational_category,
                "confidence": round(confidence, 4),
                "human_review_required": human_review_required,
            },
        )

    def review_started(self, case_id: uuid.UUID, reviewer_id: str) -> None:
        """Record that a human officer has begun reviewing a case."""
        self._repo.record(
            AuditEventType.REVIEW_STARTED,
            case_id=case_id,
            actor_id=reviewer_id,
            details={"status": "IN_REVIEW"},
        )

    def review_completed(
        self,
        case_id: uuid.UUID,
        reviewer_id: str,
        reviewer_category: str,
    ) -> None:
        """Record that a human officer completed their review and agreed with the AI."""
        self._repo.record(
            AuditEventType.REVIEW_COMPLETED,
            case_id=case_id,
            actor_id=reviewer_id,
            details={"reviewer_category": reviewer_category, "override": False},
        )

    def override_applied(
        self,
        case_id: uuid.UUID,
        reviewer_id: str,
        ai_category: str,
        reviewer_category: str,
        reason: str | None = None,
    ) -> None:
        """Record that a human officer overrode the AI's operational category."""
        self._repo.record(
            AuditEventType.OVERRIDE_APPLIED,
            case_id=case_id,
            actor_id=reviewer_id,
            details={
                "ai_category": ai_category,
                "reviewer_category": reviewer_category,
                "override": True,
                "has_reason": bool(reason),
            },
        )
