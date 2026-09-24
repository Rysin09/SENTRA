"""
Structured context input schemas for SENTRA intake.

These schemas replace the vague ``context_notes`` free-text field with
controlled, structured intake fields that support:
  - Deterministic India legal/contextual relevance mapping
  - Consistent, auditable data collection
  - Clear separation of identity from incident assessment

Privacy / Safety Invariants:
  - All identity fields are OPTIONAL and self-reported only.
  - Identity alone MUST NEVER increase distress or vulnerability scores.
  - ``PREFER_NOT_TO_SAY`` and ``UNKNOWN`` must be treated identically
    by the assessment pipeline.
  - Identity fields are used ONLY by the deterministic IndiaContextLayer,
    NEVER passed to the LLM.
  - If identity is Unknown or Prefer-not-to-say, no legal framework
    relevance shall be inferred.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Identity enums (self-reported only, all optional)
# ---------------------------------------------------------------------------


class SocialIdentityContext(str, Enum):
    """Self-reported scheduled caste/tribe status.

    Values must only be set by the complainant themselves.
    This field informs potential legal framework relevance only.
    It NEVER adjusts distress or vulnerability scores.
    """

    SC = "SC"
    ST = "ST"
    SC_ST = "SC/ST"
    NOT_APPLICABLE = "Not applicable"
    PREFER_NOT_TO_SAY = "Prefer not to say"
    UNKNOWN = "Unknown"


class MinorityCommunityContext(str, Enum):
    """Self-reported religious minority community membership.

    As defined under India's National Commission for Minorities Act, 1992:
    Muslims, Christians, Sikhs, Buddhists, Parsi/Zoroastrians, Jains.

    Values must only be set by the complainant themselves.
    This field informs potential NCM referral relevance only.
    It NEVER adjusts distress or vulnerability scores.
    """

    MUSLIM = "Muslim"
    CHRISTIAN = "Christian"
    SIKH = "Sikh"
    BUDDHIST = "Buddhist"
    PARSI_ZOROASTRIAN = "Parsi/Zoroastrian"
    JAIN = "Jain"
    NOT_APPLICABLE = "Not applicable"
    PREFER_NOT_TO_SAY = "Prefer not to say"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Incident type enum
# ---------------------------------------------------------------------------


class IncidentType(str, Enum):
    """Controlled vocabulary for incident categorisation."""

    VERBAL_ABUSE = "Verbal abuse"
    PHYSICAL_VIOLENCE = "Physical violence"
    THREAT_INTIMIDATION = "Threat / intimidation"
    DISCRIMINATION = "Discrimination"
    SOCIAL_EXCLUSION_BOYCOTT = "Social exclusion / boycott"
    DENIAL_OF_ACCESS = "Denial of access / service"
    EMPLOYMENT_DISCRIMINATION = "Employment-related discrimination"
    EDUCATION_DISCRIMINATION = "Education-related discrimination"
    HOUSING_DISCRIMINATION = "Housing-related discrimination"
    LAND_PROPERTY = "Land / property issue"
    ONLINE_HARASSMENT = "Online harassment"
    SEXUAL_GENDER_HARM = "Sexual / gender-related harm"
    POLICE_INACTION = "Police inaction / secondary victimisation"
    OTHER = "Other"


# ---------------------------------------------------------------------------
# Structured context input
# ---------------------------------------------------------------------------


class StructuredContextInput(BaseModel):
    """Structured intake context fields.

    All fields are optional (None / default). Operators and complainants must
    NEVER be pressured to disclose sensitive information.

    Sections:
      1. Identity (self-reported only, optional)
      2. Incident details
      3. Current safety
      4. Support availability
      5. Legal process status
      6. Communication needs
    """

    # ── 1. Identity (self-reported only) ─────────────────────────────────────
    social_identity_context: SocialIdentityContext = Field(
        default=SocialIdentityContext.UNKNOWN,
        description=(
            "Self-reported SC/ST status. NEVER pressured. "
            "Used only for legal framework relevance detection, "
            "NEVER for distress/vulnerability scoring."
        ),
    )
    minority_community_context: MinorityCommunityContext = Field(
        default=MinorityCommunityContext.UNKNOWN,
        description=(
            "Self-reported minority community. NEVER pressured. "
            "Used only for NCM referral relevance, "
            "NEVER for distress/vulnerability scoring."
        ),
    )

    # ── 2. Incident details ───────────────────────────────────────────────────
    incident_type: list[IncidentType] = Field(
        default_factory=list,
        description="Type(s) of incident reported. Select all that apply.",
    )
    incident_date: str | None = Field(
        default=None,
        max_length=100,
        description="Approximate date of incident (free text, not parsed).",
    )
    state: str | None = Field(
        default=None,
        max_length=100,
        description="Indian state where the incident occurred.",
    )
    district: str | None = Field(
        default=None,
        max_length=100,
        description="District where the incident occurred.",
    )
    urban_rural: Literal["Urban", "Rural", "Unknown"] | None = Field(
        default=None,
        description="Urban or rural setting.",
    )
    setting: Literal["Public", "Private", "Unknown"] | None = Field(
        default=None,
        description="Whether the incident occurred in a public or private space.",
    )

    # ── 3. Current safety ─────────────────────────────────────────────────────
    immediate_danger: bool | None = Field(
        default=None,
        description="Is the complainant in immediate danger right now?",
    )
    ongoing_threat: bool | None = Field(
        default=None,
        description="Is the threat ongoing / recurring?",
    )
    perpetrator_nearby: bool | None = Field(
        default=None,
        description="Is the perpetrator described as currently nearby?",
    )
    safe_place_available: bool | None = Field(
        default=None,
        description="Does the complainant have access to a safe place?",
    )
    needs_immediate_assistance: bool | None = Field(
        default=None,
        description="Does the complainant require immediate assistance?",
    )

    # ── 4. Support availability ────────────────────────────────────────────────
    support_available: list[str] = Field(
        default_factory=list,
        description=(
            "Support sources available to the complainant "
            "(e.g., 'Family', 'NGO', 'Local community leader')."
        ),
    )

    # ── 5. Legal process status ───────────────────────────────────────────────
    fir_filed: bool | None = Field(
        default=None,
        description="Has an FIR been filed?",
    )
    police_contacted: bool | None = Field(
        default=None,
        description="Has the police been contacted?",
    )
    previous_complaint: bool | None = Field(
        default=None,
        description="Has a previous complaint been filed about this matter?",
    )
    legal_assistance_needed: bool | None = Field(
        default=None,
        description="Does the complainant need legal assistance?",
    )
    reference_number: str | None = Field(
        default=None,
        max_length=100,
        description="Reference number from a previous complaint, FIR, or court case (optional).",
    )

    # ── 6. Communication ──────────────────────────────────────────────────────
    preferred_language: str | None = Field(
        default=None,
        max_length=60,
        description="Complainant's preferred language for communication.",
    )
    interpreter_needed: bool | None = Field(
        default=None,
        description="Does the complainant need an interpreter?",
    )
    communication_difficulty: bool | None = Field(
        default=None,
        description="Does the complainant face any communication barriers?",
    )
    accessibility_assistance: bool | None = Field(
        default=None,
        description="Does the complainant need any accessibility assistance?",
    )
