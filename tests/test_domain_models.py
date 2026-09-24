"""
Unit tests for the SENTRA domain models (Pydantic schemas).

These tests verify validation rules, invariants, and safety-critical
properties without requiring any database or external dependencies.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from sentra.domain.enums import AuditEventType, OperationalCategory
from sentra.domain.models import (
    AssessmentResult,
    AuditEvent,
    CaseInput,
)

# ── CaseInput ─────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestCaseInput:
    """Validates CaseInput schema rules."""

    def test_valid_minimal_input(self, minimal_case_input: CaseInput) -> None:
        assert minimal_case_input.consent_given is True
        assert minimal_case_input.case_id is not None

    def test_consent_must_be_true(self) -> None:
        with pytest.raises(ValidationError, match="Consent must be given"):
            CaseInput(complaint_text="Some text.", consent_given=False)

    def test_empty_complaint_text_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseInput(complaint_text="", consent_given=True)

    def test_complaint_text_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseInput(complaint_text="x" * 5001, consent_given=True)

    def test_case_id_is_unique_per_instance(self) -> None:
        a = CaseInput(complaint_text="text a", consent_given=True)
        b = CaseInput(complaint_text="text b", consent_given=True)
        assert a.case_id != b.case_id

    def test_audio_filename_optional(self) -> None:
        c = CaseInput(complaint_text="text", consent_given=True)
        assert c.audio_filename is None

    def test_context_notes_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CaseInput(
                complaint_text="text",
                consent_given=True,
                context_notes="x" * 1001,
            )


# ── AssessmentResult ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAssessmentResult:
    """Validates AssessmentResult invariants."""

    def test_default_result_is_insufficient_data(self) -> None:
        case_id = uuid.uuid4()
        result = AssessmentResult(case_id=case_id)
        assert result.operational_category == OperationalCategory.INSUFFICIENT_DATA
        assert result.human_review_required is True

    def test_insufficient_data_forces_human_review(self) -> None:
        """Safety invariant: INSUFFICIENT_DATA must always require human review."""
        case_id = uuid.uuid4()
        result = AssessmentResult(
            case_id=case_id,
            operational_category=OperationalCategory.INSUFFICIENT_DATA,
            human_review_required=False,  # should be overridden by validator
        )
        assert result.human_review_required is True

    def test_confidence_must_be_0_to_1(self) -> None:
        case_id = uuid.uuid4()
        with pytest.raises(ValidationError):
            AssessmentResult(case_id=case_id, confidence=1.5)

    def test_has_safety_flags_false_by_default(self) -> None:
        result = AssessmentResult(case_id=uuid.uuid4())
        assert result.has_safety_flags is False


# ── AuditEvent ────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestAuditEvent:
    """Validates AuditEvent schema."""

    def test_audit_event_has_unique_id(self) -> None:
        e1 = AuditEvent(event_type=AuditEventType.CASE_CREATED)
        e2 = AuditEvent(event_type=AuditEventType.CASE_CREATED)
        assert e1.event_id != e2.event_id

    def test_audit_event_details_default_empty_dict(self) -> None:
        e = AuditEvent(event_type=AuditEventType.SYSTEM_ERROR)
        assert e.details == {}


# ── Safety marker tests ───────────────────────────────────────────────────────


@pytest.mark.safety
class TestSafetyInvariants:
    """Safety-critical invariants that must never regress."""

    def test_consent_false_always_rejected(self) -> None:
        """Consent=False must always be a hard validation error."""
        with pytest.raises(ValidationError):
            CaseInput(complaint_text="Any text.", consent_given=False)

    def test_insufficient_data_never_bypasses_human_review(self) -> None:
        """INSUFFICIENT_DATA must always imply human_review_required=True."""
        result = AssessmentResult(
            case_id=uuid.uuid4(),
            operational_category=OperationalCategory.INSUFFICIENT_DATA,
            human_review_required=False,
        )
        assert result.human_review_required is True, (
            "SAFETY VIOLATION: INSUFFICIENT_DATA must force human_review_required"
        )
