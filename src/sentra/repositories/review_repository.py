"""
Review repository — data-access layer for the ``reviews`` table.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from sentra.database.models import ReviewRecord as ReviewORM
from sentra.domain.enums import OperationalCategory, ReviewStatus

logger = logging.getLogger(__name__)


class ReviewRepository:
    """Handles persistence and retrieval of human reviews."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        case_id: uuid.UUID,
        reviewer_id: str,
        status: ReviewStatus,
        ai_category: OperationalCategory,
        reviewer_category: OperationalCategory,
        overridden: bool,
        reviewer_note: str | None = None,
    ) -> ReviewORM:
        """Create a new review record."""
        record = ReviewORM(
            id=uuid.uuid4(),
            case_id=case_id,
            reviewer_id=reviewer_id,
            reviewed_at=datetime.now(tz=UTC),
            status=status.value,
            ai_category=ai_category.value,
            reviewer_category=reviewer_category.value,
            overridden=overridden,
            reviewer_note=reviewer_note,
        )
        self._session.add(record)
        return record

    def get_latest_for_case(self, case_id: uuid.UUID) -> ReviewORM | None:
        """Return the most recent review for a case."""
        stmt = (
            select(ReviewORM)
            .where(ReviewORM.case_id == case_id)
            .order_by(desc(ReviewORM.reviewed_at))
            .limit(1)
        )
        return self._session.scalars(stmt).first()
