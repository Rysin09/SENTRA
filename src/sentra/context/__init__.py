"""
SENTRA India Context Package.

Provides deterministic India-specific legal/contextual relevance assessment.

This package performs NO LLM calls. All logic is rule-based and auditable.
"""

from sentra.context.india_context_layer import (
    IndiaContextAssessment,
    IndiaContextLayer,
    PotentialFrameworkRelevance,
)
from sentra.context.legal_references import LEGAL_FRAMEWORKS, LegalFrameworkReference

__all__ = [
    "IndiaContextLayer",
    "IndiaContextAssessment",
    "PotentialFrameworkRelevance",
    "LEGAL_FRAMEWORKS",
    "LegalFrameworkReference",
]
