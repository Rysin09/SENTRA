"""
Unit tests for Phase 2 NLP schemas.
Verifies Pydantic validations, enums, list caps, and required structures.
"""

import pytest
from pydantic import ValidationError

from sentra.domain.enums import OperationalCategory
from sentra.nlp.schemas import (
    DimensionLevel,
    LLMAssessmentOutput,
    LLMDimensionAssessment,
)


def _build_valid_dimension(level: DimensionLevel) -> LLMDimensionAssessment:
    return LLMDimensionAssessment(
        level=level,
        confidence=0.8,
        evidence=["test evidence"],
        indicators=["test indicator"],
    )


def test_dimension_valid():
    dim = _build_valid_dimension(DimensionLevel.MODERATE)
    assert dim.level == DimensionLevel.MODERATE
    assert dim.confidence == 0.8
    assert dim.evidence == ["test evidence"]


def test_dimension_invalid_confidence():
    with pytest.raises(ValidationError):
        LLMDimensionAssessment(
            level=DimensionLevel.LOW,
            confidence=1.5,  # Too high
        )


def test_dimension_list_caps():
    dim = LLMDimensionAssessment(
        level=DimensionLevel.LOW,
        confidence=0.5,
        evidence=["a", "b", "c", "d"],  # 4 items
        indicators=["1", "2", "3", "4", "5"],  # 5 items
    )
    assert len(dim.evidence) == 3
    assert len(dim.indicators) == 3


def test_llm_output_valid():
    dim = _build_valid_dimension(DimensionLevel.LOW)
    output = LLMAssessmentOutput(
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
    assert output.operational_category == OperationalCategory.LOW
    assert output.overall_confidence == 0.9


def test_llm_output_insufficient_data_forces_review():
    dim = _build_valid_dimension(DimensionLevel.NONE)
    output = LLMAssessmentOutput(
        acute_distress=dim,
        fear_threat_perception=dim,
        anxiety_indicators=dim,
        trauma_related_indicators=dim,
        immediate_vulnerability=dim,
        social_support_availability=dim,
        urgency=dim,
        communication_difficulty=dim,
        overall_confidence=0.0,
        operational_category=OperationalCategory.INSUFFICIENT_DATA,
        human_review_required=False,  # Validator should override this to True
    )
    assert output.human_review_required is True
