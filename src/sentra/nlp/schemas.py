"""
Pydantic schemas for the SENTRA Phase 2 LLM structured output.

These schemas define the exact shape of data the OpenAI API must return.
All outputs are validated against these schemas before entering the pipeline.

Security:
  - These schemas do NOT appear in prompts or logs.
  - Evidence snippets are taken from complaint text — they are structural
    metadata, not raw complaint storage.
  - Schemas enforce controlled enum values and numeric ranges.

Rule 8 (Structured AI Output): All LLM outputs are parsed into strict schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from sentra.domain.enums import OperationalCategory

# ── Schema versioning ─────────────────────────────────────────────────────────

SCHEMA_VERSION = "2.0"
PROVIDER = "openai"

# ── Dimension level enum ──────────────────────────────────────────────────────


class DimensionLevel(str, Enum):
    """Controlled vocabulary for individual dimension severity.

    Maps to numeric scores:
      none     → 0.0
      low      → 0.20
      moderate → 0.45
      high     → 0.72
      critical → 0.95
    """

    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


# Map DimensionLevel → numeric score for AssessmentDimension compatibility
LEVEL_TO_SCORE: dict[DimensionLevel, float] = {
    DimensionLevel.NONE: 0.0,
    DimensionLevel.LOW: 0.20,
    DimensionLevel.MODERATE: 0.45,
    DimensionLevel.HIGH: 0.72,
    DimensionLevel.CRITICAL: 0.95,
}

# ── Per-dimension schema ──────────────────────────────────────────────────────


class LLMDimensionAssessment(BaseModel):
    """Structured assessment for one SENTRA screening dimension.

    The LLM must return exactly this structure for each of the 8 dimensions.
    Validated by Pydantic before entering the safety layer.

    Fields:
        level:      Severity level using the controlled DimensionLevel enum.
        confidence: LLM confidence in this dimension's assessment (0.0–1.0).
        evidence:   Up to 3 concise phrases directly grounded in complaint text.
        indicators: Up to 3 detected operational indicator labels.
    """

    level: DimensionLevel
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    evidence: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list,
        description="Concise phrases from complaint text (max 3).",
    )
    indicators: list[Annotated[str, Field(max_length=100)]] = Field(
        default_factory=list,
        description="Detected operational indicator labels (max 3).",
    )

    @model_validator(mode="after")
    def cap_list_lengths(self) -> LLMDimensionAssessment:
        """Enforce max list lengths as a defense against verbose output."""
        self.evidence = self.evidence[:3]
        self.indicators = self.indicators[:3]
        return self


# ── Context extraction schema ─────────────────────────────────────────────────


class TemporalContext(str, Enum):
    """Temporal framing of the incident/threat as described by the complainant."""

    IMMEDIATE = "immediate"   # Happening right now / in the next few minutes
    ONGOING = "ongoing"       # Recurring / still active threat
    RECENT = "recent"         # Within last few days, situation may still be active
    PAST = "past"             # Historical, described as resolved or no longer active
    UNKNOWN = "unknown"       # Cannot determine from text


class LLMContextExtraction(BaseModel):
    """Structured context signals extracted from the complaint text.

    All fields are nullable. The LLM must use null (None) when a signal
    is absent — it must NOT infer or fabricate missing information.

    Rule 5 (No Fabrication): Missing information must be represented as null.
    """

    incident_type: str | None = Field(
        default=None,
        max_length=100,
        description="Brief description of the incident type (e.g., 'domestic dispute').",
    )
    ongoing_threat: bool | None = Field(
        default=None,
        description="True if the threat is described as ongoing; null if unknown.",
    )
    immediate_safety_concern: bool | None = Field(
        default=None,
        description="True if an immediate safety concern is described; null if unknown.",
    )
    displacement_or_isolation: bool | None = Field(
        default=None,
        description="True if displacement or isolation is described; null if unknown.",
    )
    support_available: bool | None = Field(
        default=None,
        description="True if support is described as available; null if unknown.",
    )
    communication_difficulty_present: bool | None = Field(
        default=None,
        description="True if communication barriers are described; null if unknown.",
    )
    # ── Temporal and resolution context ──────────────────────────────────────
    temporal_context: TemporalContext = Field(
        default=TemporalContext.UNKNOWN,
        description=(
            "Temporal framing of the incident. IMMEDIATE = happening now. "
            "ONGOING = recurring/active. RECENT = last few days. "
            "PAST = historical/resolved. UNKNOWN = cannot determine."
        ),
    )
    situation_described_as_resolved: bool | None = Field(
        default=None,
        description=(
            "True if the complainant explicitly describes the situation as resolved "
            "or states they are currently safe. Null if unknown."
        ),
    )
    perpetrator_currently_present: bool | None = Field(
        default=None,
        description="True if the perpetrator is described as currently nearby. Null if unknown.",
    )
    explicit_help_request: bool | None = Field(
        default=None,
        description="True if the complainant explicitly requests immediate assistance.",
    )


# ── Full LLM output schema ────────────────────────────────────────────────────


class LLMAssessmentOutput(BaseModel):
    """The complete structured output expected from one OpenAI screening call.

    This is the strict schema that the LLM must conform to. All 8 dimensions
    are required. The operational_category uses the existing SENTRA enum.

    Rule 8 (Structured AI Output): Parsed and validated before safety layer.
    Rule 9 (Prompt Injection): LLM output validated structurally — injection
    attempts that corrupt the JSON are caught as Pydantic ValidationErrors.
    """

    # ── 8 required dimensions ─────────────────────────────────────────────────
    acute_distress: LLMDimensionAssessment
    fear_threat_perception: LLMDimensionAssessment
    anxiety_indicators: LLMDimensionAssessment
    trauma_related_indicators: LLMDimensionAssessment
    immediate_vulnerability: LLMDimensionAssessment
    social_support_availability: LLMDimensionAssessment
    urgency: LLMDimensionAssessment
    communication_difficulty: LLMDimensionAssessment

    # ── Context ───────────────────────────────────────────────────────────────
    context: LLMContextExtraction = Field(default_factory=LLMContextExtraction)

    # ── Overall assessment ────────────────────────────────────────────────────
    overall_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    operational_category: OperationalCategory
    human_review_required: bool
    safety_notes: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list,
        description="Safety observations that should be flagged for reviewers (max 5).",
    )

    @model_validator(mode="after")
    def cap_safety_notes(self) -> LLMAssessmentOutput:
        """Enforce max safety notes as defense against verbose output."""
        self.safety_notes = self.safety_notes[:5]
        return self

    @model_validator(mode="after")
    def insufficient_data_forces_review(self) -> LLMAssessmentOutput:
        """INSUFFICIENT_DATA must always require human review (Rule 6)."""
        if self.operational_category == OperationalCategory.INSUFFICIENT_DATA:
            self.human_review_required = True
        return self

    def dimension_assessments(self) -> dict[str, LLMDimensionAssessment]:
        """Return all 8 dimensions as a keyed dict for iteration."""
        return {
            "acute_distress": self.acute_distress,
            "fear_threat_perception": self.fear_threat_perception,
            "anxiety_indicators": self.anxiety_indicators,
            "trauma_related_indicators": self.trauma_related_indicators,
            "immediate_vulnerability": self.immediate_vulnerability,
            "social_support_availability": self.social_support_availability,
            "urgency": self.urgency,
            "communication_difficulty": self.communication_difficulty,
        }
