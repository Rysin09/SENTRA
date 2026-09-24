"""
Case repository — data-access layer for the ``cases`` table.

All database operations on cases go through this class. Raw complaint text
is persisted here but must never be logged or exposed casually.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from sentra.database.models import CaseRecord as CaseORM
from sentra.domain.schemas import CaseRecord, CaseSubmission

logger = logging.getLogger(__name__)


class CaseRepository:
    """Handles persistence and retrieval of case records.

    Accepts a SQLAlchemy ``Session`` injected at construction. The caller
    is responsible for committing or rolling back the session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Write ─────────────────────────────────────────────────────────────────

    def create(self, submission: CaseSubmission) -> CaseORM:
        """Persist a new case from a validated submission.

        Args:
            submission: A fully validated CaseSubmission.

        Returns:
            The newly created ORM record (not yet committed by caller).
        """
        record = CaseORM(
            id=uuid.uuid4(),
            submitted_at=datetime.now(tz=UTC),
            consent_given=submission.consent_given,
            complaint_text=submission.complaint_text,  # stored; never logged
            audio_filename=submission.audio_filename,
            context_notes=submission.context_notes,
            context_json=submission.structured_context.model_dump() if submission.structured_context else None,
        )
        self._session.add(record)
        # Do NOT log complaint_text — Rule 10
        logger.info("Case record staged for commit: case_id=%s", record.id)
        return record

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_by_id(self, case_id: uuid.UUID) -> CaseORM | None:
        """Fetch a case by its primary key. Returns None if not found."""
        return self._session.get(CaseORM, case_id)

    def list_recent(self, limit: int = 50) -> list[CaseORM]:
        """Return the most recently submitted cases, newest first."""
        from sqlalchemy import desc, select

        stmt = select(CaseORM).order_by(desc(CaseORM.submitted_at)).limit(limit)
        return list(self._session.scalars(stmt))

    # ── Mapping ───────────────────────────────────────────────────────────────

    @staticmethod
    def to_schema(record: CaseORM) -> CaseRecord:
        """Convert an ORM record to the safe read-model schema.

        Deliberately excludes ``complaint_text`` to prevent casual exposure.
        """
        return CaseRecord(
            case_id=record.id,
            submitted_at=record.submitted_at,
            consent_given=record.consent_given,
            has_audio=record.audio_filename is not None,
            context_notes=record.context_notes,
        )
