"""
Audit repository — data-access layer for the ``audit_events`` table.

Audit records must NEVER contain raw sensitive complaint content (Rule 15).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from sentra.database.models import AuditEventRecord
from sentra.domain.enums import AuditEventType

logger = logging.getLogger(__name__)


class AuditRepository:
    """Handles persistence of immutable audit trail entries.

    Accepts a SQLAlchemy ``Session`` injected at construction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        event_type: AuditEventType,
        *,
        case_id: uuid.UUID | None = None,
        actor_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditEventRecord:
        """Persist a single audit event.

        Args:
            event_type: The type of event (from AuditEventType enum).
            case_id: Associated case UUID, if applicable.
            actor_id: The system component or reviewer that triggered the event.
            details: Non-sensitive structured metadata. Must NOT include
                     raw complaint text, PII, API keys, or passwords.

        Returns:
            The newly created audit record (not yet committed by caller).
        """
        entry = AuditEventRecord(
            id=uuid.uuid4(),
            occurred_at=datetime.now(tz=UTC),
            event_type=event_type.value,
            case_id=case_id,
            actor_id=actor_id,
            details_json=details or {},
        )
        self._session.add(entry)
        logger.info(
            "Audit event staged: type=%s case_id=%s actor=%s",
            event_type.value,
            case_id,
            actor_id,
        )
        return entry
