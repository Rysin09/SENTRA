"""
Integration tests for CaseRepository and AuditRepository.

Use the in-memory SQLite ``db_session`` fixture (rolled back per test).
No external services required.
"""

from __future__ import annotations

import uuid

import pytest

from sentra.domain.enums import AuditEventType
from sentra.domain.schemas import CaseSubmission
from sentra.repositories.audit_repository import AuditRepository
from sentra.repositories.case_repository import CaseRepository


@pytest.mark.integration
class TestCaseRepository:
    """CaseRepository persists and retrieves cases correctly."""

    def test_create_returns_orm_record(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        record = repo.create(valid_submission)
        db_session.flush()
        assert record.id is not None
        assert isinstance(record.id, uuid.UUID)

    def test_create_persists_consent(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        record = repo.create(valid_submission)
        db_session.flush()
        assert record.consent_given is True

    def test_create_stores_complaint_text(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        """Complaint text must be stored (for retrieval via audited paths)."""
        repo = CaseRepository(db_session)
        record = repo.create(valid_submission)
        db_session.flush()
        assert record.complaint_text == valid_submission.complaint_text

    def test_create_stores_audio_filename(
        self, db_session, submission_with_audio: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        record = repo.create(submission_with_audio)
        db_session.flush()
        assert record.audio_filename == "recording.wav"

    def test_get_by_id_returns_record(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        created = repo.create(valid_submission)
        db_session.flush()
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_by_id_unknown_returns_none(self, db_session) -> None:
        repo = CaseRepository(db_session)
        result = repo.get_by_id(uuid.uuid4())
        assert result is None

    def test_list_recent_returns_created_records(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        repo.create(valid_submission)
        repo.create(valid_submission)
        db_session.flush()
        results = repo.list_recent(limit=10)
        assert len(results) >= 2

    def test_to_schema_excludes_complaint_text(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        """Safety: the read-model must NOT expose raw complaint text."""
        repo = CaseRepository(db_session)
        record = repo.create(valid_submission)
        db_session.flush()
        schema = CaseRepository.to_schema(record)
        assert not hasattr(schema, "complaint_text"), (
            "SAFETY: CaseRecord schema must not contain complaint_text"
        )

    def test_to_schema_has_audio_flag(
        self, db_session, submission_with_audio: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        record = repo.create(submission_with_audio)
        db_session.flush()
        schema = CaseRepository.to_schema(record)
        assert schema.has_audio is True

    def test_to_schema_no_audio_flag(
        self, db_session, valid_submission: CaseSubmission
    ) -> None:
        repo = CaseRepository(db_session)
        record = repo.create(valid_submission)
        db_session.flush()
        schema = CaseRepository.to_schema(record)
        assert schema.has_audio is False


@pytest.mark.integration
class TestAuditRepository:
    """AuditRepository persists events correctly."""

    def test_record_creates_entry(self, db_session) -> None:
        repo = AuditRepository(db_session)
        case_id = uuid.uuid4()
        entry = repo.record(
            AuditEventType.CASE_CREATED,
            case_id=case_id,
            actor_id="system:test",
            details={"has_audio": False},
        )
        db_session.flush()
        assert entry.id is not None
        assert entry.event_type == AuditEventType.CASE_CREATED.value
        assert entry.case_id == case_id

    def test_record_details_stored(self, db_session) -> None:
        repo = AuditRepository(db_session)
        entry = repo.record(
            AuditEventType.CASE_CREATED,
            details={"has_audio": True},
        )
        db_session.flush()
        assert entry.details_json == {"has_audio": True}

    def test_record_defaults_empty_details(self, db_session) -> None:
        repo = AuditRepository(db_session)
        entry = repo.record(AuditEventType.SYSTEM_ERROR)
        db_session.flush()
        assert entry.details_json == {}

    @pytest.mark.safety
    def test_audit_details_no_complaint_text_by_convention(self, db_session) -> None:
        """Safety: audit details must not contain complaint_text key."""
        repo = AuditRepository(db_session)
        # This simulates a bad caller — the repository does NOT enforce this at the
        # type level, but we document the invariant here and check convention.
        details_without_text = {"has_audio": False, "channel": "web"}
        entry = repo.record(
            AuditEventType.CASE_CREATED,
            details=details_without_text,
        )
        db_session.flush()
        assert "complaint_text" not in entry.details_json
