"""
Multi-factor confidence calculator for SENTRA AI screening.

Replaces the raw LLM-invented confidence passthrough.

The output is labeled "AI screening confidence" and represents the quality
and reliability of the AI screening output — NOT:
  - probability that an offence occurred
  - probability that the complainant is truthful
  - legal confidence
  - medical confidence

Rule 14 (Confidence): Confidence is an assessment-quality signal, not certainty.
Rule 5 (No Fabrication): Missing information never boosts confidence.
Rule 6 (Insufficient Data): Low confidence forces human_review_required.
"""

from __future__ import annotations

from sentra.nlp.normalizer import NormalizedText, TextQuality
from sentra.nlp.schemas import DimensionLevel, LLMAssessmentOutput

# ---------------------------------------------------------------------------
# Scoring weights and thresholds
# ---------------------------------------------------------------------------

# Minimum confidence below which human review is forced by the pipeline
CONFIDENCE_THRESHOLD_FOR_REVIEW: float = 0.40

# Maximum confidence the calculator can award — leaves room for uncertainty
MAX_CONFIDENCE: float = 0.92

# Weight for each contributing factor (must sum to 1.0)
_W_TEXT_QUALITY: float = 0.20
_W_LLM_DIM_CONFIDENCE: float = 0.25
_W_EVIDENCE_COVERAGE: float = 0.20
_W_CONSISTENCY: float = 0.20
_W_CONTEXT_COMPLETENESS: float = 0.15


def calculate_confidence(
    normalized: NormalizedText,
    llm_output: LLMAssessmentOutput,
) -> float:
    """Calculate multi-factor AI screening confidence.

    Args:
        normalized:  The NormalizedText from the pre-processing step.
        llm_output:  The validated LLM assessment output (post-safety-layer).

    Returns:
        A float in [0.0, MAX_CONFIDENCE] representing AI screening confidence.
        This is NOT legal or medical certainty.

    Penalties applied for:
        - FAILED or DEGRADED text quality
        - Prompt injection detection
        - Low LLM dimension confidence values
        - Missing evidence across dimensions
        - Contradiction between dimension levels and overall category
        - Safety notes present (model uncertainty indicator)
        - Missing structured context
    """
    score = 0.0

    # ------------------------------------------------------------------
    # Factor 1: Text quality (0.0 → 1.0)
    # ------------------------------------------------------------------
    text_quality_score = _score_text_quality(normalized)
    score += _W_TEXT_QUALITY * text_quality_score

    # ------------------------------------------------------------------
    # Factor 2: Average LLM per-dimension confidence (0.0 → 1.0)
    # We use the per-dimension confidence values as a sanity signal.
    # If the LLM itself is uncertain about every dimension, we trust the
    # overall assessment less. We average and apply a mild ceiling.
    # ------------------------------------------------------------------
    dim_confidence_score = _score_dim_confidence(llm_output)
    score += _W_LLM_DIM_CONFIDENCE * dim_confidence_score

    # ------------------------------------------------------------------
    # Factor 3: Evidence coverage (0.0 → 1.0)
    # % of dimensions that have at least one evidence phrase.
    # ------------------------------------------------------------------
    evidence_score = _score_evidence_coverage(llm_output)
    score += _W_EVIDENCE_COVERAGE * evidence_score

    # ------------------------------------------------------------------
    # Factor 4: Consistency (0.0 → 1.0)
    # Penalise contradictions between dimension levels and overall category.
    # ------------------------------------------------------------------
    consistency_score = _score_consistency(llm_output)
    score += _W_CONSISTENCY * consistency_score

    # ------------------------------------------------------------------
    # Factor 5: Context completeness (0.0 → 1.0)
    # Reward having structured context signals available.
    # ------------------------------------------------------------------
    context_score = _score_context_completeness(llm_output)
    score += _W_CONTEXT_COMPLETENESS * context_score

    # ------------------------------------------------------------------
    # Penalties
    # ------------------------------------------------------------------

    # Injection detection: severe confidence penalty
    if normalized.injection_detected:
        score *= 0.60

    # Safety notes: model signalled uncertainty → reduce confidence
    if llm_output.safety_notes:
        score *= max(0.75, 1.0 - 0.05 * len(llm_output.safety_notes))

    # Overall LLM confidence is very low → apply proportional penalty
    if llm_output.overall_confidence < 0.40:
        score *= llm_output.overall_confidence / 0.40

    # ------------------------------------------------------------------
    # Clamp to valid range
    # ------------------------------------------------------------------
    return round(min(max(score, 0.0), MAX_CONFIDENCE), 4)


# ---------------------------------------------------------------------------
# Private scoring helpers
# ---------------------------------------------------------------------------


def _score_text_quality(normalized: NormalizedText) -> float:
    """Score text quality as a [0.0, 1.0] signal."""
    if normalized.quality == TextQuality.FAILED:
        return 0.0
    if normalized.quality == TextQuality.DEGRADED:
        return 0.35

    # GOOD quality — reward richer text (more tokens = more evidence)
    # Saturates at ~200 tokens (plenty of evidence)
    token_ratio = min(normalized.token_count / 200.0, 1.0)
    return 0.60 + 0.40 * token_ratio


def _score_dim_confidence(llm_output: LLMAssessmentOutput) -> float:
    """Average LLM per-dimension confidence, capped at 0.9."""
    dims = llm_output.dimension_assessments()
    if not dims:
        return 0.0
    avg = sum(d.confidence for d in dims.values()) / len(dims)
    return min(avg, 0.90)


def _score_evidence_coverage(llm_output: LLMAssessmentOutput) -> float:
    """Fraction of dimensions that have at least one evidence phrase."""
    dims = llm_output.dimension_assessments()
    if not dims:
        return 0.0
    dims_with_evidence = sum(1 for d in dims.values() if d.evidence)
    return dims_with_evidence / len(dims)


def _score_consistency(llm_output: LLMAssessmentOutput) -> float:
    """Score consistency between dimension levels and overall category.

    Contradictions (e.g. CRITICAL dimension but LOW overall) reduce this score.
    The safety layer may already have corrected some, but we still penalise
    any remaining tension.
    """
    from sentra.domain.enums import OperationalCategory

    dims = llm_output.dimension_assessments()
    cat = llm_output.operational_category

    # Count HIGH/CRITICAL dimensions (excluding social_support which is inverse)
    high_critical_count = sum(
        1
        for name, d in dims.items()
        if name != "social_support_availability"
        and d.level in (DimensionLevel.HIGH, DimensionLevel.CRITICAL)
    )

    if cat in (OperationalCategory.CRITICAL, OperationalCategory.HIGH):
        # Good: category matches elevated dimensions
        if high_critical_count >= 2:
            return 1.0
        if high_critical_count == 1:
            return 0.80
        # High/Critical category but no high/critical dims — inconsistent
        return 0.40

    if cat == OperationalCategory.LOW:
        # Good: no elevated dimensions
        if high_critical_count == 0:
            return 1.0
        # LOW but some high dims — contradiction
        return max(0.30, 1.0 - 0.20 * high_critical_count)

    if cat == OperationalCategory.MODERATE:
        # Moderate is expected to have some but not all elevated dims
        return 0.85

    # INSUFFICIENT_DATA
    return 0.70


def _score_context_completeness(llm_output: LLMAssessmentOutput) -> float:
    """Score completeness of extracted context signals.

    Context signals are useful but not required. Reward non-null signals.
    """
    ctx = llm_output.context
    signals = [
        ctx.incident_type,
        ctx.ongoing_threat,
        ctx.immediate_safety_concern,
        ctx.displacement_or_isolation,
        ctx.support_available,
        ctx.communication_difficulty_present,
    ]
    # Count signals that are not None
    non_null = sum(1 for s in signals if s is not None)
    return non_null / len(signals)
