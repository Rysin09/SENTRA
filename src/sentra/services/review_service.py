"""
Review service — handles the human review workflow.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from sentra.audit.service import AuditService
from sentra.database.models import ReviewRecord
from sentra.database.session import get_session
from sentra.domain.enums import OperationalCategory, ReviewStatus
from sentra.repositories.assessment_repository import AssessmentRepository
from sentra.repositories.review_repository import ReviewRepository

logger = logging.getLogger(__name__)


class ReviewService:
    """Handles human review of AI screening assessments."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def submit_review(
        self,
        case_id: uuid.UUID,
        reviewer_id: str,
        reviewer_category: OperationalCategory,
        reviewer_note: str | None = None,
    ) -> ReviewRecord:
        """Submit a human review for a case.

        Args:
            case_id: The case being reviewed.
            reviewer_id: Identifier for the human reviewer.
            reviewer_category: The final operational category decided by the human.
            reviewer_note: Optional rationale or notes from the reviewer.
        """
        if self._session is not None:
            return self._submit_with_session(
                self._session, case_id, reviewer_id, reviewer_category, reviewer_note
            )
        with get_session() as session:
            return self._submit_with_session(
                session, case_id, reviewer_id, reviewer_category, reviewer_note
            )

    @staticmethod
    def _submit_with_session(
        session: Session,
        case_id: uuid.UUID,
        reviewer_id: str,
        reviewer_category: OperationalCategory,
        reviewer_note: str | None,
    ) -> ReviewRecord:
        assessment_repo = AssessmentRepository(session)
        review_repo = ReviewRepository(session)
        audit_svc = AuditService(session)

        # 1. Fetch original assessment
        record = assessment_repo.get_by_case_id(case_id)
        if not record:
            raise ValueError(f"No assessment found for case {case_id}")

        ai_category = OperationalCategory(record.operational_category)
        is_override = ai_category != reviewer_category

        status = ReviewStatus.OVERRIDDEN if is_override else ReviewStatus.COMPLETED

        # 2. Persist review decision
        review_record = review_repo.create(
            case_id=case_id,
            reviewer_id=reviewer_id,
            status=status,
            ai_category=ai_category,
            reviewer_category=reviewer_category,
            overridden=is_override,
            reviewer_note=reviewer_note,
        )
        session.flush()

        # 3. Audit trail
        if is_override:
            audit_svc.override_applied(
                case_id=case_id,
                reviewer_id=reviewer_id,
                ai_category=ai_category.value,
                reviewer_category=reviewer_category.value,
                reason=reviewer_note,
            )
            logger.info(
                "Review override: case_id=%s ai=%s human=%s",
                case_id,
                ai_category.value,
                reviewer_category.value,
            )
        else:
            audit_svc.review_completed(
                case_id=case_id,
                reviewer_id=reviewer_id,
                reviewer_category=reviewer_category.value,
            )
            logger.info("Review completed: case_id=%s status=%s", case_id, status.value)

        return review_record

    def get_latest_review(self, case_id: uuid.UUID) -> ReviewRecord | None:
        """Fetch the most recent review for a case."""
        if self._session is not None:
            repo = ReviewRepository(self._session)
            return repo.get_latest_for_case(case_id)

        with get_session() as session:
            repo = ReviewRepository(session)
            return repo.get_latest_for_case(case_id)
