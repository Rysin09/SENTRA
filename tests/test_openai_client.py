"""
Unit tests for the OpenAI client wrapper.
Uses pytest-mock to mock the OpenAI SDK; no real API calls are made.
"""

from unittest.mock import MagicMock

import openai
import pytest

from sentra.domain.enums import OperationalCategory
from sentra.nlp.openai_client import ScreeningAPIError, call_screening
from sentra.nlp.schemas import LLMAssessmentOutput
from tests.test_nlp_schemas import _build_valid_dimension


@pytest.fixture
def mock_openai_client(mocker):
    # Mock get_settings to return a dummy key
    mock_settings = mocker.patch("sentra.nlp.openai_client.get_settings")
    settings_instance = MagicMock()
    settings_instance.openai_enabled = True
    settings_instance.openai_api_key.get_secret_value.return_value = "sk-test"
    settings_instance.openai_model = "gpt-4o"
    settings_instance.openai_timeout_seconds = 30
    settings_instance.openai_max_retries = 2
    mock_settings.return_value = settings_instance

    # Mock openai.OpenAI
    mock_client_class = mocker.patch("sentra.nlp.openai_client.openai.OpenAI")
    mock_client_instance = MagicMock()
    mock_client_class.return_value = mock_client_instance
    return mock_client_instance


def _create_mock_response(parsed_output: LLMAssessmentOutput | None, refusal: str | None = None):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.parsed = parsed_output
    mock_message.refusal = refusal
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response


def test_call_screening_success(mock_openai_client):
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
        overall_confidence=0.9,
        operational_category=OperationalCategory.LOW,
        human_review_required=False,
    )

    mock_openai_client.beta.chat.completions.parse.return_value = _create_mock_response(valid_output)

    result = call_screening("test text")
    assert result.operational_category == OperationalCategory.LOW
    assert result.overall_confidence == 0.9


def test_call_screening_model_refusal(mock_openai_client):
    mock_openai_client.beta.chat.completions.parse.return_value = _create_mock_response(None, refusal="I cannot process this.")

    with pytest.raises(ScreeningAPIError):
        call_screening("test text")


def test_call_screening_api_timeout(mock_openai_client):
    # Pass a valid request object mock to APITimeoutError
    mock_openai_client.beta.chat.completions.parse.side_effect = openai.APITimeoutError(request=MagicMock())

    with pytest.raises(ScreeningAPIError, match="timeout"):
        call_screening("test text")


def test_call_screening_auth_error(mock_openai_client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.content = b'{"error": {"message": "Invalid API Key"}}'

    mock_openai_client.beta.chat.completions.parse.side_effect = openai.AuthenticationError(
        message="Invalid API Key",
        response=mock_response,
        body={"error": {"message": "Invalid API Key"}},
    )

    with pytest.raises(ScreeningAPIError, match="Authentication"):
        call_screening("test text")
