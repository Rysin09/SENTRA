"""
SENTRA NLP & Text Analysis Module.

Phase 2: LLM-powered text screening with deterministic safety.
"""

from sentra.nlp.normalizer import (
    NormalizedText,
    normalize,
)
from sentra.nlp.openai_client import ScreeningAPIError, call_screening
from sentra.nlp.prompts import SYSTEM_PROMPT, build_user_payload
from sentra.nlp.safety_layer import apply_safety_rules
from sentra.nlp.schemas import (
    DimensionLevel,
    LLMAssessmentOutput,
    LLMContextExtraction,
    LLMDimensionAssessment,
    TemporalContext,
)

__all__ = [
    "normalize",
    "NormalizedText",
    "call_screening",
    "ScreeningAPIError",
    "apply_safety_rules",
    "LLMAssessmentOutput",
    "LLMDimensionAssessment",
    "LLMContextExtraction",
    "DimensionLevel",
    "TemporalContext",
    "SYSTEM_PROMPT",
    "build_user_payload",
]
