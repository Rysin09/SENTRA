"""
Deterministic safety rules applied after LLM inference (Phase 2).

This module is the final gatekeeper before an AssessmentResult is produced.
All rules are deterministic, transparent, and testable.

Invariants guaranteed by this layer:
  - HIGH or CRITICAL category → human_review_required = True
  - INSUFFICIENT_DATA → human_review_required = True
  - Confidence < 0.40 → human_review_required = True
  - HIGH/CRITICAL dimension + LOW overall → bump to MODERATE minimum
  - Combined HIGH urgency + HIGH vulnerability → bump to HIGH minimum
  - Past/resolved temporal context → add reviewer note, do NOT auto-escalate
  - Social support noted as HIGH → protective factor note added
  - Safety rules may only escalate or hold — never silently downgrade
"""

from __future__ import annotations

from sentra.domain.enums import OperationalCategory
from sentra.nlp.schemas import DimensionLevel, LLMAssessmentOutput, TemporalContext

# Category severity order (higher index = higher severity)
_SEVERITY: dict[OperationalCategory, int] = {
    OperationalCategory.INSUFFICIENT_DATA: 0,
    OperationalCategory.LOW: 1,
    OperationalCategory.MODERATE: 2,
    OperationalCategory.HIGH: 3,
    OperationalCategory.CRITICAL: 4,
}

# Reverse map
_SEVERITY_TO_CAT: dict[int, OperationalCategory] = {v: k for k, v in _SEVERITY.items()}


def _bump(
    current: OperationalCategory,
    minimum: OperationalCategory,
) -> OperationalCategory:
    """Ensure current category is at least 'minimum'; never downgrade."""
    if _SEVERITY[current] < _SEVERITY[minimum]:
        return minimum
    return current


def apply_safety_rules(output: LLMAssessmentOutput) -> LLMAssessmentOutput:
    """Apply deterministic post-LLM safety rules.

    Mutates and returns the output with any necessary escalations and
    safety notes added.

    Args:
        output: A validated LLMAssessmentOutput from the OpenAI call.

    Returns:
        The same object with safety rules applied. The output is NEVER
        downgraded — only escalated or held.
    """
    notes: list[str] = list(output.safety_notes)

    # ------------------------------------------------------------------
    # Rule S1: HIGH or CRITICAL overall → always require human review
    # ------------------------------------------------------------------
    if output.operational_category in (OperationalCategory.HIGH, OperationalCategory.CRITICAL):
        output.human_review_required = True
        notes.append(
            f"S1: {output.operational_category.value} category requires mandatory human review."
        )

    # ------------------------------------------------------------------
    # Rule S2: INSUFFICIENT_DATA → always require human review
    # ------------------------------------------------------------------
    if output.operational_category == OperationalCategory.INSUFFICIENT_DATA:
        output.human_review_required = True
        notes.append("S2: INSUFFICIENT_DATA — insufficient evidence for reliable screening.")

    # ------------------------------------------------------------------
    # Rule S3: Low LLM confidence → require human review
    # ------------------------------------------------------------------
    if output.overall_confidence < 0.40:
        output.human_review_required = True
        notes.append(
            f"S3: Low LLM confidence ({output.overall_confidence:.2f}) "
            "— human review required."
        )

    # ------------------------------------------------------------------
    # Rule S4: Dimension-category contradiction detection
    #
    # If any non-inverse dimension is HIGH/CRITICAL but overall is LOW →
    # bump to MODERATE minimum, force review.
    #
    # If any non-inverse dimension is CRITICAL but overall is below HIGH →
    # bump to HIGH minimum, force review.
    # ------------------------------------------------------------------
    dims = output.dimension_assessments()

    critical_dims = [
        name
        for name, d in dims.items()
        if name != "social_support_availability"
        and d.level == DimensionLevel.CRITICAL
    ]
    high_or_critical_dims = [
        name
        for name, d in dims.items()
        if name != "social_support_availability"
        and d.level in (DimensionLevel.HIGH, DimensionLevel.CRITICAL)
    ]

    if critical_dims and _SEVERITY[output.operational_category] < _SEVERITY[OperationalCategory.HIGH]:
        output.operational_category = _bump(output.operational_category, OperationalCategory.HIGH)
        output.human_review_required = True
        notes.append(
            f"S4a: Contradictory signal — CRITICAL dimension(s) [{', '.join(critical_dims)}] "
            f"with sub-HIGH overall. Escalated to HIGH."
        )
    elif high_or_critical_dims and _SEVERITY[output.operational_category] < _SEVERITY[OperationalCategory.MODERATE]:
        output.operational_category = _bump(output.operational_category, OperationalCategory.MODERATE)
        output.human_review_required = True
        notes.append(
            f"S4b: Contradictory signal — HIGH/CRITICAL dimension(s) "
            f"[{', '.join(high_or_critical_dims)}] with LOW overall. Escalated to MODERATE."
        )

    # ------------------------------------------------------------------
    # Rule S5: Combined urgency + vulnerability → force HIGH minimum
    #
    # If urgency AND immediate_vulnerability are both HIGH or CRITICAL,
    # the combination is operationally significant even if other dims are low.
    # ------------------------------------------------------------------
    urgency_level = dims.get("urgency")
    vuln_level = dims.get("immediate_vulnerability")
    if (
        urgency_level
        and vuln_level
        and urgency_level.level in (DimensionLevel.HIGH, DimensionLevel.CRITICAL)
        and vuln_level.level in (DimensionLevel.HIGH, DimensionLevel.CRITICAL)
        and _SEVERITY[output.operational_category] < _SEVERITY[OperationalCategory.HIGH]
    ):
        output.operational_category = _bump(output.operational_category, OperationalCategory.HIGH)
        output.human_review_required = True
        notes.append(
            "S5: High urgency + high immediate vulnerability combination "
            "— escalated to HIGH minimum."
        )

    # ------------------------------------------------------------------
    # Rule S6: Temporal context — resolved/past situation
    #
    # If the complainant describes the situation as past/resolved, add a
    # reviewer note. Do NOT automatically downgrade — the reviewer must
    # make that determination. But we should NOT auto-escalate based on
    # urgency if situation_described_as_resolved is True.
    # ------------------------------------------------------------------
    ctx = output.context
    if ctx.situation_described_as_resolved is True:
        notes.append(
            "S6: Temporal context — complainant appears to describe situation as resolved "
            "or currently safe. Reviewer should verify before any escalation."
        )
    elif ctx.temporal_context == TemporalContext.PAST:
        notes.append(
            "S6: Temporal context — incident appears historical. "
            "Current safety should be verified by reviewer."
        )
    elif ctx.temporal_context in (TemporalContext.IMMEDIATE, TemporalContext.ONGOING):
        if not output.human_review_required:
            notes.append(
                "S6: Temporal context indicates active/immediate situation — "
                "priority review recommended."
            )

    # ------------------------------------------------------------------
    # Rule S7: Social support as protective factor
    #
    # HIGH social support is a protective signal. Note it for the reviewer
    # but do NOT change the operational category — support availability
    # does not reduce the reality of the incident.
    # ------------------------------------------------------------------
    social_support = dims.get("social_support_availability")
    if social_support and social_support.level in (DimensionLevel.HIGH, DimensionLevel.CRITICAL):
        notes.append(
            "S7: Protective factor detected — social support appears available. "
            "Reviewer should confirm and factor into response planning."
        )

    # ------------------------------------------------------------------
    # Rule S8: Explicit immediate help request
    # ------------------------------------------------------------------
    if ctx.explicit_help_request is True:
        output.human_review_required = True
        notes.append(
            "S8: Explicit request for immediate help detected — priority review required."
        )

    # ------------------------------------------------------------------
    # Rule S9: Perpetrator currently present
    # ------------------------------------------------------------------
    if ctx.perpetrator_currently_present is True:
        output.human_review_required = True
        notes.append(
            "S9: Perpetrator described as currently present — immediate review required."
        )

    output.safety_notes = notes
    return output
