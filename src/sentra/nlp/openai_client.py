"""
OpenAI API client wrapper for SENTRA text screening.

This module encapsulates the OpenAI SDK. It provides a single interface
for structured NLP screening and handles authentication, timeouts, retries,
and Pydantic schema validation.

Security:
  - The API key is read from Settings.secret_str and never logged.
  - The complaint text is never logged here.
  - All API failures are caught and raised as a safe custom exception.

Rule 11 (LLM Failure Handling): Network timeouts, model unavailability,
and rate limits must raise exceptions so the caller can fall back safely
to INSUFFICIENT_DATA and human_review_required.
"""

from __future__ import annotations

import logging

import openai
from pydantic import ValidationError

from sentra.config.settings import get_settings
from sentra.nlp.prompts import SYSTEM_PROMPT, build_user_payload
from sentra.nlp.schemas import LLMAssessmentOutput

logger = logging.getLogger(__name__)


class ScreeningAPIError(Exception):
    """Raised when the OpenAI API fails, times out, or returns invalid data.

    This error indicates that automated screening cannot proceed. The pipeline
    must catch this and safely fall back to INSUFFICIENT_DATA.
    """


def call_screening(
    normalized_text: str,
    context_notes: str | None = None,
    structured_context_summary: str | None = None,
) -> LLMAssessmentOutput:
    """Execute a single structured OpenAI API call to assess the complaint.

    Args:
        normalized_text:           Sanitized complaint text (untrusted user input).
        context_notes:             Optional operator context (trusted).
        structured_context_summary: Optional plain-text summary of structured
                                    intake context fields (safe to pass, no identity).

    Returns:
        A validated LLMAssessmentOutput matching the strict Pydantic schema.

    Raises:
        ScreeningAPIError: If the API call fails, the model is unavailable,
                           or the returned JSON cannot be parsed/validated.
    """
    settings = get_settings()

    if not settings.openai_enabled:
        logger.error("OpenAI screening called but OPENAI_API_KEY is not set.")
        raise ScreeningAPIError("OpenAI API key not configured.")

    # Initialize client with timeout and retry configuration
    # Disable compression to workaround an httpx/python3.13 zlib decompression bug
    client = openai.OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
        default_headers={"Accept-Encoding": "identity"},
    )

    user_payload = build_user_payload(
        normalized_text,
        context_notes,
        structured_context_summary,
    )

    try:
        # Use OpenAI structured outputs capability
        response = client.beta.chat.completions.parse(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload},
            ],
            response_format=LLMAssessmentOutput,
            # We want deterministic/low-variance extraction, not creative writing.
            temperature=0.1,
            top_p=0.9,
        )

        message = response.choices[0].message

        # Check if the model refused to answer (e.g. triggered OpenAI safety filters)
        if message.refusal:
            logger.warning("OpenAI model refused to assess the text: %s", message.refusal)
            raise ScreeningAPIError("Model refused to assess the input.")

        # Ensure we got parsed output
        if not message.parsed:
             raise ScreeningAPIError("Model did not return parsed structured output.")

        return message.parsed

    except openai.AuthenticationError as e:
        logger.error("OpenAI authentication failed. Check API key.")
        raise ScreeningAPIError("Authentication failed.") from e
    except openai.NotFoundError as e:
        logger.error("OpenAI model '%s' not found or unavailable.", settings.openai_model)
        raise ScreeningAPIError(f"Configured model {settings.openai_model} is unavailable.") from e
    except openai.RateLimitError as e:
        logger.error("OpenAI rate limit exceeded.")
        raise ScreeningAPIError("Rate limit exceeded.") from e
    except openai.APITimeoutError as e:
        logger.error("OpenAI API call timed out after %d seconds.", settings.openai_timeout_seconds)
        raise ScreeningAPIError("API timeout.") from e
    except openai.APIError as e:
        logger.error("OpenAI API error: %s", e)
        raise ScreeningAPIError(f"API error: {e}") from e
    except ValidationError as e:
        logger.error("Failed to validate OpenAI JSON output against schema.")
        # We do NOT log the raw JSON because it may contain sensitive text.
        raise ScreeningAPIError("Invalid structured output from model.") from e
    except Exception as e:
        logger.exception("Unexpected error during OpenAI screening.")
        raise ScreeningAPIError("Unexpected screening error.") from e
