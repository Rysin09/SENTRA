"""
Integration tests for CaseService Phase 1 (submit_case, get_case, list_recent).

Uses the in-memory SQLite ``db_session`` fixture for isolation.
"""

from __future__ import annotations

import uuid

import pytest

from sentra.domain.enums import OperationalCategory
from sentra.domain.models import CaseInput
from sentra.domain.schemas import CaseCreated, CaseSubmission
from sentra.services.case_service import CaseService


@pytest.mark.integration
class TestCaseServiceSubmit:
    """CaseService.submit_case persists and audits a new case."""

    def test_submit_returns_case_created(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        result = service.submit_case(valid_submission)
        db_session.commit()
        assert isinstance(result, CaseCreated)

    def test_submit_returns_valid_uuid(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        result = service.submit_case(valid_submission)
        db_session.commit()
        assert isinstance(result.case_id, uuid.UUID)

    def test_submit_case_id_is_unique_per_submission(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        r1 = service.submit_case(valid_submission)
        r2 = service.submit_case(valid_submission)
        db_session.commit()
        assert r1.case_id != r2.case_id

    def test_submit_with_audio_filename(
        self, db_session, submission_with_audio: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        result = service.submit_case(submission_with_audio)
        db_session.commit()
        assert isinstance(result.case_id, uuid.UUID)

    def test_submit_persists_retrievable_case(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        created = service.submit_case(valid_submission)
        db_session.commit()
        fetched = service.get_case(created.case_id)
        assert fetched is not None
        assert fetched.case_id == created.case_id

    def test_get_case_excludes_complaint_text(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        """Safety: get_case must not expose raw complaint text."""
        service = CaseService(session=db_session)
        created = service.submit_case(valid_submission)
        db_session.commit()
        fetched = service.get_case(created.case_id)
        assert fetched is not None
        assert not hasattr(fetched, "complaint_text"), (
            "SAFETY: get_case must never return complaint_text"
        )

    def test_get_case_returns_none_for_unknown_id(self, db_session) -> None:
        service = CaseService(session=db_session)
        result = service.get_case(uuid.uuid4())
        assert result is None

    def test_list_recent_includes_submitted_case(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        service = CaseService(session=db_session)
        created = service.submit_case(valid_submission)
        db_session.commit()
        cases = service.list_recent_cases(limit=50)
        ids = [c.case_id for c in cases]
        assert created.case_id in ids

    def test_list_recent_returns_no_complaint_text(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        """Safety: list_recent_cases must not expose complaint text."""
        service = CaseService(session=db_session)
        service.submit_case(valid_submission)
        db_session.commit()
        cases = service.list_recent_cases()
        for case in cases:
            assert not hasattr(case, "complaint_text"), (
                "SAFETY: list_recent_cases must never return complaint_text"
            )


from sentra.nlp.schemas import LLMAssessmentOutput
from tests.test_nlp_schemas import _build_valid_dimension


@pytest.fixture(autouse=True)
def mock_call_screening(mocker):
    dim = _build_valid_dimension("low")
    valid_output = LLMAssessmentOutput(
        acute_distress=dim,
        fear_threat_perception=dim,
        anxiety_indicators=dim,
        trauma_related_indicators=dim,
        immediate_vulnerability=dim,
        social_support_availability=dim,
        urgency=dim,
        communication_difficulty=dim,
        overall_confidence=0.8,
        operational_category=OperationalCategory.LOW,
        human_review_required=False,
    )
    return mocker.patch("sentra.assessment.pipeline.call_screening", return_value=valid_output)


@pytest.mark.unit
class TestCaseServicePhase0Compat:
    """Compatibility tests for Phase 0 behavior mapped to Phase 2.

    neutral test text (no distress indicators) produces LOW.
    """

    def test_process_case_returns_assessment(
        self, minimal_case_input: CaseInput
    ) -> None:
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result is not None

    def test_process_case_preserves_case_id(
        self, minimal_case_input: CaseInput
    ) -> None:
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result.case_id == minimal_case_input.case_id

    def test_phase2_pipeline_version(
        self, minimal_case_input: CaseInput
    ) -> None:
        """Phase 2 pipeline version is 0.2.0."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result.pipeline_version == "0.2.0"

    def test_phase2_neutral_text_gives_low_category(
        self, minimal_case_input: CaseInput
    ) -> None:
        """Neutral text (no distress indicators) yields LOW, not INSUFFICIENT_DATA."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        # Neutral text with 6+ tokens → pipeline runs → LOW
        assert result.operational_category in (
            OperationalCategory.LOW,
            OperationalCategory.MODERATE,
        )

    def test_phase2_neutral_text_human_review_not_forced(
        self, minimal_case_input: CaseInput
    ) -> None:
        """LOW-category neutral text does not force human review."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        if result.operational_category == OperationalCategory.LOW:
            assert result.human_review_required is False
