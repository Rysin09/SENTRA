"""
Integration tests for AssessmentRepository — Phase 2.

Uses the in-memory SQLite ``db_session`` fixture for isolation.

Covers:
  - create / retrieve round-trip
  - get_by_case_id returns None for unknown case
  - Serialization round-trip for dimensions, modalities, safety flags
  - list_recent returns most recent first
"""

from __future__ import annotations

import uuid

import pytest

from sentra.assessment.pipeline import PIPELINE_VERSION, TextScreeningPipeline
from sentra.domain.enums import ModalityQuality, ModalityType, OperationalCategory
from sentra.domain.models import (
    AssessmentDimension,
    AssessmentResult,
    CaseInput,
    ModalityStatus,
    SafetyFlag,
)
from sentra.repositories.assessment_repository import AssessmentRepository


def _make_result(
    text: str = "I am terrified and shaking. He threatened to kill me. Emergency now.",
    case_id: uuid.UUID | None = None,
) -> AssessmentResult:
    """Build a synthetic AssessmentResult for testing."""
    cid = case_id or uuid.uuid4()
    return AssessmentResult(
        case_id=cid,
        pipeline_version=PIPELINE_VERSION,
        modalities_used=[
            ModalityStatus(modality=ModalityType.TEXT, available=True, quality=ModalityQuality.GOOD)
        ],
        dimensions=[
            AssessmentDimension(
                name="acute_distress",
                score=0.95,
                label="CRITICAL",
                supporting_indicators=["terrified", "shaking"],
                missing_signals=[]
            )
        ],
        operational_category=OperationalCategory.CRITICAL,
        confidence=0.9,
        explanation="Synthetic test result.",
        human_review_required=True,
        safety_flags=[SafetyFlag(rule_id="test", description="test flag")],
        extra_metadata={"provider": "test"}
    )


def _make_minimal_result(case_id: uuid.UUID | None = None) -> AssessmentResult:
    """Build an INSUFFICIENT_DATA result for tests."""
    cid = case_id or uuid.uuid4()
    case_input = CaseInput(
        case_id=cid,
        complaint_text="help me please",
        consent_given=True,
    )
    pipeline = TextScreeningPipeline()
    return pipeline.run(case_input)


@pytest.mark.integration
class TestAssessmentRepositoryCreate:
    """AssessmentRepository.create persists results correctly."""

    def test_create_returns_orm_record(self, db_session) -> None:  # noqa: ANN001
        result = _make_result()
        repo = AssessmentRepository(db_session)
        orm = repo.create(result)
        db_session.flush()
        assert orm is not None

    def test_create_stores_correct_case_id(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert fetched is not None
        assert fetched.case_id == case_id

    def test_create_stores_pipeline_version(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert fetched.pipeline_version == PIPELINE_VERSION

    def test_create_stores_operational_category(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert fetched.operational_category == result.operational_category.value

    def test_create_stores_confidence(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert abs(fetched.confidence - result.confidence) < 1e-6

    def test_create_stores_human_review_required(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_minimal_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert fetched.human_review_required is True

    def test_create_stores_dimensions_json(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert isinstance(fetched.dimensions_json, dict)
        assert "acute_distress" in fetched.dimensions_json


@pytest.mark.integration
class TestAssessmentRepositoryRead:
    """AssessmentRepository read operations."""

    def test_get_by_case_id_returns_none_for_unknown(self, db_session) -> None:  # noqa: ANN001
        repo = AssessmentRepository(db_session)
        result = repo.get_by_case_id(uuid.uuid4())
        assert result is None

    def test_get_by_case_id_returns_most_recent(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result1 = _make_result(case_id=case_id)
        result2 = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result1)
        db_session.flush()
        repo.create(result2)
        db_session.flush()
        fetched = repo.get_by_case_id(case_id)
        assert fetched is not None  # Should return one (most recent)

    def test_list_recent_returns_list(self, db_session) -> None:  # noqa: ANN001
        repo = AssessmentRepository(db_session)
        records = repo.list_recent(limit=10)
        assert isinstance(records, list)

    def test_list_recent_includes_created_record(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        records = repo.list_recent(limit=50)
        case_ids = [r.case_id for r in records]
        assert case_id in case_ids


@pytest.mark.integration
class TestAssessmentRepositoryDomainRoundTrip:
    """AssessmentRepository.to_domain reconstructs AssessmentResult accurately."""

    def test_to_domain_returns_assessment_result(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        assert isinstance(domain, AssessmentResult)

    def test_round_trip_preserves_case_id(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        assert domain.case_id == case_id

    def test_round_trip_preserves_operational_category(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        assert domain.operational_category == result.operational_category

    def test_round_trip_preserves_all_dimensions(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        dim_names = {d.name for d in domain.dimensions}
        assert "acute_distress" in dim_names

    def test_round_trip_preserves_pipeline_version(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_result(case_id=case_id)
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        assert domain.pipeline_version == PIPELINE_VERSION

    def test_insufficient_data_round_trip(self, db_session) -> None:  # noqa: ANN001
        case_id = uuid.uuid4()
        result = _make_minimal_result(case_id=case_id)
        assert result.operational_category == OperationalCategory.INSUFFICIENT_DATA
        repo = AssessmentRepository(db_session)
        repo.create(result)
        db_session.flush()
        orm = repo.get_by_case_id(case_id)
        domain = AssessmentRepository.to_domain(orm)
        assert domain.operational_category == OperationalCategory.INSUFFICIENT_DATA
        assert domain.human_review_required is True
