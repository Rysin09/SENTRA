"""
SENTRA Phase 2 Screening Pipeline (LLM-Powered).

Orchestrates the flow:
Text → Normalizer → Insufficient Data Guard → OpenAI LLM → Safety Layer → AssessmentResult

Rule 7 (Fail Safe): Catch all LLM failures and fallback to INSUFFICIENT_DATA.
"""

from __future__ import annotations

import logging
import uuid

from sentra.config.settings import get_settings
from sentra.domain.enums import ModalityQuality, ModalityType, OperationalCategory
from sentra.domain.models import (
    AssessmentDimension,
    AssessmentResult,
    CaseInput,
    IndiaContextAssessment,
    ModalityStatus,
    SafetyFlag,
)
from sentra.nlp import (
    ScreeningAPIError,
    apply_safety_rules,
    call_screening,
    normalize,
)
from sentra.nlp.schemas import SCHEMA_VERSION, LLMAssessmentOutput

logger = logging.getLogger(__name__)

PIPELINE_VERSION = "0.2.0"


def _safe_insufficient_data(case_id: uuid.UUID, reason: str) -> AssessmentResult:
    """Build a safe INSUFFICIENT_DATA result for use outside the pipeline class.

    Used by case_service.run_screening() when the case record cannot be found
    or when screening cannot proceed before a pipeline instance is available.

    Args:
        case_id: The case UUID for which screening cannot proceed.
        reason:  A non-sensitive description of why screening failed.

    Returns:
        An AssessmentResult with INSUFFICIENT_DATA and human_review_required=True.
    """
    dim_names = [
        "acute_distress",
        "fear_threat_perception",
        "anxiety_indicators",
        "trauma_related_indicators",
        "immediate_vulnerability",
        "social_support_availability",
        "urgency",
        "communication_difficulty",
    ]
    empty_dims = [
        AssessmentDimension(
            name=name,
            score=0.0,
            label="NONE",
            supporting_indicators=[],
            missing_signals=["unavailable"],
        )
        for name in dim_names
    ]
    return AssessmentResult(
        case_id=case_id,
        pipeline_version=PIPELINE_VERSION,
        modalities_used=[],
        dimensions=empty_dims,
        operational_category=OperationalCategory.INSUFFICIENT_DATA,
        confidence=0.0,
        explanation=(
            f"Insufficient data for reliable screening — Human Review Required. ({reason})"
        ),
        human_review_required=True,
        safety_flags=[
            SafetyFlag(
                rule_id="fallback_case_not_found",
                description=reason,
                forces_human_review=True,
            )
        ],
        extra_metadata={"fallback": True, "reason": reason, "schema_version": SCHEMA_VERSION},
    )


class TextScreeningPipeline:
    """Orchestrates the Phase 2 LLM text screening process."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def run(self, case_input: CaseInput) -> AssessmentResult:
        """Run the complete text screening pipeline.

        Args:
            case_input: Validated case input domain model.

        Returns:
            AssessmentResult: The final operational assessment.
        """
        logger.info("Starting LLM text screening for case %s", case_input.case_id)

        # 1. Normalize and sanitize input
        normalized = normalize(case_input.complaint_text)

        # Modality tracking
        ctx_available = bool(case_input.context_notes) or bool(
            getattr(case_input, "structured_context", None)
        )
        text_modality = ModalityStatus(
            modality=ModalityType.TEXT,
            available=True,
            quality=ModalityQuality.GOOD,
            notes=f"tokens={normalized.token_count}; injection={normalized.injection_detected}",
        )
        context_modality = ModalityStatus(
            modality=ModalityType.CONTEXT,
            available=ctx_available,
            quality=ModalityQuality.GOOD if ctx_available else ModalityQuality.NOT_PROVIDED,
        )
        modalities = [text_modality, context_modality]

        # 2. Insufficient Data Guard (Before LLM)
        if not normalized.is_screenable:
            logger.info(
                "Text not screenable for case %s — falling back to INSUFFICIENT_DATA.",
                case_input.case_id,
            )
            text_modality.quality = ModalityQuality.FAILED
            text_modality.notes = f"{text_modality.notes}; rejected_pre_llm"
            return self._build_fallback(
                case_input=case_input,
                modalities=modalities,
                reason="Insufficient text length or meaningful content for reliable AI screening.",
            )

        # 3. Build structured context summary for LLM (if available)
        structured_ctx_summary = _build_structured_context_summary(case_input)

        # 4. LLM Screening Call
        try:
            llm_output = call_screening(
                normalized_text=normalized.clean_text,
                context_notes=case_input.context_notes,
                structured_context_summary=structured_ctx_summary,
            )
        except ScreeningAPIError as e:
            logger.warning("LLM screening failed for case %s: %s", case_input.case_id, e)
            return self._build_fallback(
                case_input=case_input,
                modalities=modalities,
                reason=f"AI screening unavailable: {e}",
            )

        # 5. Deterministic Safety Layer
        safe_output = apply_safety_rules(llm_output)

        # 6. Multi-factor confidence calculation
        from sentra.assessment.confidence import calculate_confidence
        calibrated_confidence = calculate_confidence(normalized, safe_output)

        # 7. India Context Layer (deterministic legal relevance mapping)
        from sentra.context.india_context_layer import IndiaContextLayer
        india_layer = IndiaContextLayer()
        india_context = india_layer.assess(
            structured_context=getattr(case_input, "structured_context", None),
            llm_output=safe_output,
        )

        # 8. Map to Domain Model
        return self._map_to_domain(
            case_input=case_input,
            modalities=modalities,
            llm_output=safe_output,
            calibrated_confidence=calibrated_confidence,
            india_context=india_context,
        )

    def _map_to_domain(
        self,
        case_input: CaseInput,
        modalities: list[ModalityStatus],
        llm_output: LLMAssessmentOutput,
        calibrated_confidence: float = 0.0,
        india_context: IndiaContextAssessment | None = None,
    ) -> AssessmentResult:
        """Map the safe structured LLM output to the SENTRA AssessmentResult."""
        from sentra.nlp.schemas import LEVEL_TO_SCORE

        # Map dimensions — keep indicators and evidence separate for reviewer clarity
        dimensions = []
        for dim_name, dim_assessment in llm_output.dimension_assessments().items():
            # Indicators: short keyword/phrase signals
            # Evidence: longer text excerpts supporting the dimension score
            # Both are shown to reviewers; evidence is richer context
            indicators = dim_assessment.indicators[:3]
            evidence = dim_assessment.evidence[:3]
            dimensions.append(
                AssessmentDimension(
                    name=dim_name,
                    score=LEVEL_TO_SCORE[dim_assessment.level],
                    label=dim_assessment.level.value.upper(),
                    supporting_indicators=indicators + evidence,
                    missing_signals=[],
                )
            )

        # Map safety flags from safety layer notes
        safety_flags = [
            SafetyFlag(
                rule_id=f"rule_{i}",
                description=note,
                forces_human_review=True,
            )
            for i, note in enumerate(llm_output.safety_notes)
        ]

        # Explanation
        if llm_output.operational_category == OperationalCategory.INSUFFICIENT_DATA:
            explanation = "Insufficient data for reliable AI-assisted screening."
        else:
            explanation = (
                f"{llm_output.operational_category.value} operational priority. "
                "This is an AI-assisted screening indicator only — not a clinical diagnosis."
            )

        return AssessmentResult(
            case_id=case_input.case_id,
            pipeline_version=PIPELINE_VERSION,
            modalities_used=modalities,
            dimensions=dimensions,
            operational_category=llm_output.operational_category,
            confidence=calibrated_confidence,
            explanation=explanation,
            safety_flags=safety_flags,
            human_review_required=llm_output.human_review_required,
            extra_metadata={
                "provider": "openai",
                "model": self.settings.openai_model,
                "schema_version": SCHEMA_VERSION,
                "llm_raw_confidence": llm_output.overall_confidence,
                "context_signals": llm_output.context.model_dump(),
            },
            india_context=india_context,
        )

    def _build_fallback(
        self, case_input: CaseInput, modalities: list[ModalityStatus], reason: str
    ) -> AssessmentResult:
        """Build a safe fallback result when screening cannot proceed."""
        # Baseline empty dimensions
        dim_names = [
            "acute_distress",
            "fear_threat_perception",
            "anxiety_indicators",
            "trauma_related_indicators",
            "immediate_vulnerability",
            "social_support_availability",
            "urgency",
            "communication_difficulty",
        ]
        empty_dims = [
            AssessmentDimension(
                name=name,
                score=0.0,
                label="NONE",
                supporting_indicators=[],
                missing_signals=["unavailable"],
            )
            for name in dim_names
        ]

        return AssessmentResult(
            case_id=case_input.case_id,
            pipeline_version=PIPELINE_VERSION,
            modalities_used=modalities,
            dimensions=empty_dims,
            operational_category=OperationalCategory.INSUFFICIENT_DATA,
            confidence=0.0,
            explanation=reason,
            human_review_required=True,
            safety_flags=[
                SafetyFlag(
                    rule_id="fallback_01",
                    description=reason,
                    forces_human_review=True,
                )
            ],
            extra_metadata={
                "provider": "openai",
                "model": self.settings.openai_model,
                "schema_version": SCHEMA_VERSION,
                "fallback": True,
            },
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _build_structured_context_summary(case_input: CaseInput) -> str | None:
    """Build a plain-text summary of structured context fields for the LLM.

    The structured context is passed as a SEPARATE section from the complaint
    text to prevent the LLM from confusing intake officer context with
    complainant narrative.

    Returns None if no structured context is available.

    NOTE: Identity fields (social_identity_context, minority_community_context)
    are deliberately NOT included in the LLM payload. Identity is used only by
    the deterministic IndiaContextLayer — the LLM must NOT be influenced by it.
    """
    sc = getattr(case_input, "structured_context", None)
    if sc is None:
        return None

    lines: list[str] = []

    # Incident details (safe to include)
    if sc.incident_type:
        types = ", ".join(t.value if hasattr(t, "value") else str(t) for t in sc.incident_type)
        lines.append(f"Incident type(s): {types}")
    if sc.state:
        loc = sc.state
        if sc.district:
            loc += f", {sc.district}"
        lines.append(f"Location: {loc}")
    if sc.urban_rural:
        lines.append(f"Setting: {sc.urban_rural}")

    # Current safety context (safe to include — informs urgency)
    if sc.immediate_danger is True:
        lines.append("Current status: Immediate danger reported")
    elif sc.immediate_danger is False:
        lines.append("Current status: No immediate danger reported")
    if sc.ongoing_threat is True:
        lines.append("Threat status: Ongoing threat reported")
    if sc.perpetrator_nearby is True:
        lines.append("Perpetrator: Described as currently nearby")
    if sc.safe_place_available is True:
        lines.append("Safe location: Available")
    elif sc.safe_place_available is False:
        lines.append("Safe location: Not available")
    if sc.needs_immediate_assistance is True:
        lines.append("Assistance: Immediate assistance requested")

    # Support context
    if sc.support_available:
        lines.append(f"Support available: {', '.join(sc.support_available)}")

    # Communication
    if sc.communication_difficulty is True:
        lines.append("Communication difficulty: Reported")
    if sc.interpreter_needed is True:
        lines.append("Interpreter: Required")
    if sc.preferred_language:
        lines.append(f"Preferred language: {sc.preferred_language}")

    # Legal process (informs context, not LLM legal analysis)
    if sc.fir_filed is True:
        lines.append("FIR: Filed")
    elif sc.fir_filed is False:
        lines.append("FIR: Not yet filed")
    if sc.police_contacted is True:
        lines.append("Police: Contacted")

    return "\n".join(lines) if lines else None
