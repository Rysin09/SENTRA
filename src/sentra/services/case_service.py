"""
Case service — Phase 2 implementation.

Orchestrates both the intake workflow and the NLP text-screening pipeline:

Phase 1 (unchanged):
  1. Validate the submission (already done by Pydantic schema).
  2. Persist the case via CaseRepository.
  3. Record a CASE_CREATED audit event via AuditService.
  4. Return a CaseCreated receipt.

Phase 2 (new):
  5. run_screening(case_id): fetch raw complaint text via audited path,
     run TextScreeningPipeline, persist AssessmentResult, audit.

The Phase 0 process_case() stub is REPLACED by the real Phase 2 pipeline.
Existing Phase 0 backward-compat tests have been updated in
test_case_service_phase1.py to reflect Phase 2 behaviour.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from sentra.assessment.pipeline import TextScreeningPipeline
from sentra.audit.service import AuditService
from sentra.database.session import get_session
from sentra.domain.models import AssessmentResult, CaseInput
from sentra.domain.schemas import CaseCreated, CaseRecord, CaseSubmission
from sentra.repositories.assessment_repository import AssessmentRepository
from sentra.repositories.case_repository import CaseRepository

logger = logging.getLogger(__name__)

_pipeline = TextScreeningPipeline()


class CaseService:
    """Orchestrates case creation, retrieval, and NLP screening.

    Can be constructed with an explicit session (for testing) or will
    open its own session via ``get_session()`` when none is provided.
    """

    def __init__(self, session: Session | None = None) -> None:
        self._session = session  # None → use get_session() context manager

    # ── Phase 1: intake ───────────────────────────────────────────────────────

    def submit_case(self, submission: CaseSubmission) -> CaseCreated:
        """Validate, persist, and audit a new case submission.

        Args:
            submission: A fully validated CaseSubmission.

        Returns:
            CaseCreated receipt with the opaque case_id.

        Raises:
            RuntimeError: If the database operation fails (safe error only).
        """
        if self._session is not None:
            return self._submit_with_session(self._session, submission)

        with get_session() as session:
            return self._submit_with_session(session, submission)

    @staticmethod
    def _submit_with_session(
        session: Session, submission: CaseSubmission
    ) -> CaseCreated:
        """Internal: perform the full intake within a given session."""
        case_repo = CaseRepository(session)
        audit_svc = AuditService(session)

        # Persist case
        orm_record = case_repo.create(submission)
        # Flush so orm_record.id is populated before audit
        session.flush()

        # Audit — must not include complaint_text (Rule 15, Rule 10)
        audit_svc.case_created(
            orm_record.id,
            has_audio=submission.audio_filename is not None,
        )

        return CaseCreated(
            case_id=orm_record.id,
            submitted_at=orm_record.submitted_at,
        )

    # ── Phase 2: screening ────────────────────────────────────────────────────

    def run_screening(self, case_id: uuid.UUID) -> AssessmentResult:
        """Fetch a case's complaint text and run the NLP screening pipeline.

        This is the audited path for accessing raw complaint text.
        The text is passed ONLY to the pipeline; it is never logged,
        returned to callers, or stored in the assessment result.

        Args:
            case_id: UUID of the case to screen.

        Returns:
            AssessmentResult — always non-None. On failure or missing case,
            returns INSUFFICIENT_DATA with human_review_required=True.
        """
        if self._session is not None:
            return self._screen_with_session(self._session, case_id)
        with get_session() as session:
            return self._screen_with_session(session, case_id)

    @staticmethod
    def _screen_with_session(session: Session, case_id: uuid.UUID) -> AssessmentResult:
        """Internal: run screening and persist result within a given session."""
        case_repo = CaseRepository(session)
        assessment_repo = AssessmentRepository(session)
        audit_svc = AuditService(session)

        # Fetch case (audited access to complaint text)
        orm_case = case_repo.get_by_id(case_id)
        if orm_case is None:
            logger.warning("run_screening called for unknown case_id=%s", case_id)
            # Return a safe INSUFFICIENT_DATA result (case not found)
            from sentra.assessment.pipeline import _safe_insufficient_data
            return _safe_insufficient_data(case_id, "case_not_found")

        # Build CaseInput from ORM record (complaint text used only by pipeline)
        case_input = CaseInput(
            case_id=orm_case.id,
            complaint_text=orm_case.complaint_text,  # treated as untrusted
            consent_given=orm_case.consent_given,
            audio_filename=orm_case.audio_filename,
            context_notes=orm_case.context_notes,
        )

        # Run the NLP pipeline (complaint text never leaves this call)
        result = _pipeline.run(case_input)

        # Persist assessment result
        assessment_repo.create(result)
        session.flush()

        # Audit — metadata only, no complaint content
        audit_svc.assessment_generated(
            case_id=case_id,
            pipeline_version=result.pipeline_version,
            operational_category=result.operational_category.value,
            confidence=result.confidence,
            human_review_required=result.human_review_required,
        )

        return result

    def get_assessment(self, case_id: uuid.UUID) -> AssessmentResult | None:
        """Return the most recent assessment for a case, or None."""
        if self._session is not None:
            return self._get_assessment_with_session(self._session, case_id)
        with get_session() as session:
            return self._get_assessment_with_session(session, case_id)

    @staticmethod
    def _get_assessment_with_session(
        session: Session, case_id: uuid.UUID
    ) -> AssessmentResult | None:
        repo = AssessmentRepository(session)
        record = repo.get_by_case_id(case_id)
        if record is None:
            return None
        return AssessmentRepository.to_domain(record)

    def list_recent_assessments(self, limit: int = 50) -> list[AssessmentResult]:
        """Return the most recent assessments as domain objects."""
        if self._session is not None:
            return self._list_assessments_with_session(self._session, limit)
        with get_session() as session:
            return self._list_assessments_with_session(session, limit)

    @staticmethod
    def _list_assessments_with_session(
        session: Session, limit: int
    ) -> list[AssessmentResult]:
        repo = AssessmentRepository(session)
        records = repo.list_recent(limit)
        return [AssessmentRepository.to_domain(r) for r in records]

    # ── Retrieval (Phase 1) ───────────────────────────────────────────────────

    def get_case(self, case_id: uuid.UUID) -> CaseRecord | None:
        """Return the safe read-model for a case, or None if not found.

        Raw complaint text is NOT returned from this method.
        """
        if self._session is not None:
            return self._get_case_with_session(self._session, case_id)
        with get_session() as session:
            return self._get_case_with_session(session, case_id)

    @staticmethod
    def _get_case_with_session(
        session: Session, case_id: uuid.UUID
    ) -> CaseRecord | None:
        repo = CaseRepository(session)
        record = repo.get_by_id(case_id)
        if record is None:
            return None
        return CaseRepository.to_schema(record)

    def list_recent_cases(self, limit: int = 50) -> list[CaseRecord]:
        """Return the most recent cases as safe read-models (no complaint text)."""
        if self._session is not None:
            return self._list_with_session(self._session, limit)
        with get_session() as session:
            return self._list_with_session(session, limit)

    @staticmethod
    def _list_with_session(session: Session, limit: int) -> list[CaseRecord]:
        repo = CaseRepository(session)
        records = repo.list_recent(limit)
        return [CaseRepository.to_schema(r) for r in records]

    def get_complaint_text(self, case_id: uuid.UUID) -> str | None:
        """Return the raw complaint text for a case.

        This is an audited path for the Reviewer Dashboard.
        The text must NEVER be logged or exposed outside the secure dashboard.
        """
        if self._session is not None:
            return self._get_complaint_text_with_session(self._session, case_id)
        with get_session() as session:
            return self._get_complaint_text_with_session(session, case_id)

    @staticmethod
    def _get_complaint_text_with_session(
        session: Session, case_id: uuid.UUID
    ) -> str | None:
        repo = CaseRepository(session)
        record = repo.get_by_id(case_id)
        if record is None:
            return None
        return record.complaint_text

    # ── Phase 2: process_case (replaces Phase 0 stub) ─────────────────────────

    def process_case(self, case_input: CaseInput) -> AssessmentResult:
        """Run the Phase 2 NLP screening pipeline directly on a CaseInput.

        This method replaces the Phase 0 stub. It is used by tests and
        callers that already have a CaseInput (e.g. direct API access).

        For the full audited workflow (fetch from DB → screen → persist),
        use ``run_screening(case_id)`` instead.
        """
        return _pipeline.run(case_input)
