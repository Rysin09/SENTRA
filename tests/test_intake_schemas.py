"""
Unit tests for Phase 1 domain schemas (CaseSubmission, CaseCreated, CaseRecord).

No database required — pure Pydantic validation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentra.domain.schemas import CaseSubmission


@pytest.mark.unit
class TestCaseSubmission:
    """CaseSubmission validation rules."""

    def test_valid_minimal_submission(self, valid_submission: CaseSubmission) -> None:
        assert valid_submission.consent_given is True
        assert len(valid_submission.complaint_text) >= 10

    def test_consent_false_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Informed consent is required"):
            CaseSubmission(
                complaint_text="A valid complaint text here.",
                consent_given=False,
            )

    def test_text_too_short_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseSubmission(complaint_text="short", consent_given=True)

    def test_empty_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseSubmission(complaint_text="", consent_given=True)

    def test_whitespace_only_text_rejected(self) -> None:
        # Use a long whitespace string so it passes min_length but fails the
        # custom non-whitespace validator.
        with pytest.raises(ValidationError, match="non-whitespace"):
            CaseSubmission(complaint_text=" " * 20, consent_given=True)

    def test_text_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseSubmission(complaint_text="x" * 5001, consent_given=True)

    def test_audio_filename_optional(self) -> None:
        s = CaseSubmission(
            complaint_text="Valid complaint text here.", consent_given=True
        )
        assert s.audio_filename is None

    def test_audio_filename_accepted(self, submission_with_audio: CaseSubmission) -> None:
        assert submission_with_audio.audio_filename == "recording.wav"

    def test_context_notes_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseSubmission(
                complaint_text="Valid complaint text here.",
                consent_given=True,
                context_notes="x" * 1001,
            )

    def test_audio_filename_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseSubmission(
                complaint_text="Valid complaint text here.",
                consent_given=True,
                audio_filename="a" * 513,
            )


@pytest.mark.unit
@pytest.mark.safety
class TestCaseSubmissionSafetyInvariants:
    """Safety-critical CaseSubmission invariants that must never regress."""

    def test_consent_false_always_rejected(self) -> None:
        """Consent=False must always be a hard validation error — no bypass."""
        with pytest.raises(ValidationError):
            CaseSubmission(
                complaint_text="Any valid complaint text here.",
                consent_given=False,
            )

    def test_blank_text_always_rejected(self) -> None:
        """Empty/whitespace text must always be rejected."""
        # Short strings hit min_length; the 20-space string hits the custom validator.
        for bad_text in ["", "   ", "\t\n", " " * 20]:
            with pytest.raises(ValidationError):
                CaseSubmission(complaint_text=bad_text, consent_given=True)

