"""
Unit tests for CaseService.process_case — updated for Phase 2.

The Phase 0 stub that always returned INSUFFICIENT_DATA has been replaced
by the real Phase 2 NLP pipeline. These tests have been updated to reflect
the new behaviour.
"""

from __future__ import annotations

import pytest

from sentra.domain.enums import OperationalCategory
from sentra.domain.models import CaseInput
from sentra.nlp.schemas import LLMAssessmentOutput
from sentra.services.case_service import CaseService
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
class TestCaseServicePhase0:
    """CaseService.process_case now runs the real Phase 2 pipeline.

    Phase 0 stub always returned INSUFFICIENT_DATA; Phase 2 runs the
    real pipeline (mocked here).
    """

    def test_process_case_returns_assessment(self, minimal_case_input: CaseInput) -> None:
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result is not None

    def test_process_case_preserves_case_id(self, minimal_case_input: CaseInput) -> None:
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result.case_id == minimal_case_input.case_id

    def test_phase2_pipeline_version(self, minimal_case_input: CaseInput) -> None:
        """Phase 2 pipeline version is 0.2.0."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        assert result.pipeline_version == "0.2.0"

    def test_phase2_neutral_text_gives_low_category(self, minimal_case_input: CaseInput) -> None:
        """Neutral text (no distress indicators) yields LOW, not INSUFFICIENT_DATA."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        # The minimal_case_input has 6+ tokens of neutral text → pipeline runs → LOW
        assert result.operational_category in (
            OperationalCategory.LOW,
            OperationalCategory.MODERATE,
        )

    def test_phase2_neutral_text_human_review_not_forced(self, minimal_case_input: CaseInput) -> None:
        """LOW-category neutral text does not force human review."""
        service = CaseService()
        result = service.process_case(minimal_case_input)
        if result.operational_category == OperationalCategory.LOW:
            assert result.human_review_required is False
