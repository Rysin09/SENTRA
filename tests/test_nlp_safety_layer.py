"""
Unit tests for the deterministic safety layer.
"""

from sentra.domain.enums import OperationalCategory
from sentra.nlp.safety_layer import apply_safety_rules
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
        indicators=[],
    )


def _build_base_output(category: OperationalCategory) -> LLMAssessmentOutput:
    return LLMAssessmentOutput(
        acute_distress=_build_valid_dimension(DimensionLevel.LOW),
        fear_threat_perception=_build_valid_dimension(DimensionLevel.LOW),
        anxiety_indicators=_build_valid_dimension(DimensionLevel.LOW),
        trauma_related_indicators=_build_valid_dimension(DimensionLevel.LOW),
        immediate_vulnerability=_build_valid_dimension(DimensionLevel.LOW),
        social_support_availability=_build_valid_dimension(DimensionLevel.LOW),
        urgency=_build_valid_dimension(DimensionLevel.LOW),
        communication_difficulty=_build_valid_dimension(DimensionLevel.LOW),
        overall_confidence=0.9,
        operational_category=category,
        human_review_required=False,
    )


def test_high_critical_forces_review():
    out_high = _build_base_output(OperationalCategory.HIGH)
    out_crit = _build_base_output(OperationalCategory.CRITICAL)

    safe_high = apply_safety_rules(out_high)
    safe_crit = apply_safety_rules(out_crit)

    assert safe_high.human_review_required is True
    assert any("HIGH" in n for n in safe_high.safety_notes)

    assert safe_crit.human_review_required is True
    assert any("CRITICAL" in n for n in safe_crit.safety_notes)


def test_zero_confidence_forces_review():
    out = _build_base_output(OperationalCategory.LOW)
    out.overall_confidence = 0.0

    safe_out = apply_safety_rules(out)
    assert safe_out.human_review_required is True
    assert any("0" in n for n in safe_out.safety_notes)


def test_contradiction_detection():
    out = _build_base_output(OperationalCategory.LOW)
    out.acute_distress.level = DimensionLevel.CRITICAL

    safe_out = apply_safety_rules(out)
    # S4a: CRITICAL dimension + LOW overall → escalated to HIGH (was MODERATE in old logic)
    assert safe_out.operational_category == OperationalCategory.HIGH
    assert safe_out.human_review_required is True
    assert any("Contradictory" in n or "S4" in n for n in safe_out.safety_notes)


def test_social_support_highlight():
    out = _build_base_output(OperationalCategory.MODERATE)
    out.social_support_availability.level = DimensionLevel.HIGH

    safe_out = apply_safety_rules(out)
    # MODERATE category stays MODERATE — social support does NOT change category
    assert safe_out.operational_category == OperationalCategory.MODERATE
    # Safety notes should mention protective factor (S7)
    assert any("protective" in n.lower() or "S7" in n for n in safe_out.safety_notes)


def test_high_dimension_with_low_overall():
    """HIGH dimension + LOW overall → bump to MODERATE minimum (S4b rule)."""
    out = _build_base_output(OperationalCategory.LOW)
    out.acute_distress.level = DimensionLevel.HIGH

    safe_out = apply_safety_rules(out)
    assert safe_out.operational_category == OperationalCategory.MODERATE
    assert safe_out.human_review_required is True
    assert any("S4b" in n for n in safe_out.safety_notes)


def test_urgency_plus_vulnerability_escalates_to_high():
    """HIGH urgency + HIGH vulnerability + MODERATE overall → bump to HIGH (S5 rule)."""
    out = _build_base_output(OperationalCategory.MODERATE)
    out.urgency.level = DimensionLevel.HIGH
    out.immediate_vulnerability.level = DimensionLevel.HIGH

    safe_out = apply_safety_rules(out)
    assert safe_out.operational_category == OperationalCategory.HIGH
    assert safe_out.human_review_required is True
    assert any("S5" in n for n in safe_out.safety_notes)
