"""
Integration tests for the LLM-powered text screening pipeline.
Uses pytest-mock to mock the OpenAI API layer, testing the orchestrator.
"""


import pytest

from sentra.assessment.pipeline import PIPELINE_VERSION, TextScreeningPipeline
from sentra.domain.enums import OperationalCategory
from sentra.domain.models import CaseInput
from sentra.nlp.openai_client import ScreeningAPIError
from sentra.nlp.schemas import LLMAssessmentOutput
from tests.test_nlp_schemas import _build_valid_dimension


@pytest.fixture
def mock_call_screening(mocker):
    return mocker.patch("sentra.assessment.pipeline.call_screening")


def test_pipeline_success(mock_call_screening):
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
        overall_confidence=0.85,
        operational_category=OperationalCategory.MODERATE,
        human_review_required=False,
    )
    mock_call_screening.return_value = valid_output

    pipeline = TextScreeningPipeline()
    case_input = CaseInput(complaint_text="This is a sufficiently long complaint text for testing.", consent_given=True)

    result = pipeline.run(case_input)

    assert result.operational_category == OperationalCategory.MODERATE
    # Confidence is now calculated using the multi-factor calculator, not raw passthrough
    assert result.confidence > 0.60
    assert not result.human_review_required
    assert result.pipeline_version == PIPELINE_VERSION
    assert result.extra_metadata["provider"] == "openai"
    assert result.extra_metadata["schema_version"] == "2.0"
    mock_call_screening.assert_called_once()


def test_pipeline_insufficient_data_pre_llm(mock_call_screening):
    pipeline = TextScreeningPipeline()
    # Too short -> rejected by normalizer, LLM not called
    case_input = CaseInput(complaint_text="Too short.", consent_given=True)

    result = pipeline.run(case_input)

    assert result.operational_category == OperationalCategory.INSUFFICIENT_DATA
    assert result.human_review_required is True
    assert result.confidence == 0.0
    mock_call_screening.assert_not_called()


def test_pipeline_api_failure_fallback(mock_call_screening):
    mock_call_screening.side_effect = ScreeningAPIError("API timeout")

    pipeline = TextScreeningPipeline()
    case_input = CaseInput(complaint_text="This is a sufficiently long complaint text for testing.", consent_given=True)

    result = pipeline.run(case_input)

    assert result.operational_category == OperationalCategory.INSUFFICIENT_DATA
    assert result.human_review_required is True
    assert result.confidence == 0.0
    assert result.extra_metadata.get("fallback") is True
