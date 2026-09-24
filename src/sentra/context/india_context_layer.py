"""
India-specific legal/contextual relevance layer — Phase 2.

This layer applies DETERMINISTIC rules (no LLM call) to surface potentially
relevant legal frameworks based on:
  - Self-reported identity context (SC/ST, minority community)
  - Structured intake context (incident type, safety, legal status)
  - Complaint text signals (detected by the LLM, passed as context)

CRITICAL CONSTRAINTS:
  - NEVER infers or assumes identity from complaint text alone.
  - NEVER concludes that an offence occurred under any law.
  - NEVER makes a legal determination.
  - ALWAYS sets requires_human_legal_review = True on every output.
  - If identity is UNKNOWN or PREFER_NOT_TO_SAY → no identity-based framework flagged.
  - Framework relevance is advisory for human reviewers, not a legal finding.
  - Identity alone (with no incident facts) MUST NOT trigger framework relevance.

Source governance:
  All legal references sourced from official Indian government sources.
  See legal_references.py for versioned reference configuration.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from sentra.context.legal_references import (
    LEGAL_FRAMEWORKS,
    LegalFrameworkReference,
)
from sentra.domain.context_schemas import (
    IncidentType,
    MinorityCommunityContext,
    SocialIdentityContext,
    StructuredContextInput,
)
from sentra.nlp.schemas import LLMAssessmentOutput

# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class PotentialFrameworkRelevance(BaseModel):
    """A single potentially relevant legal framework, surfaced for human review.

    DISCLAIMER: This is a screening indicator only. It does NOT constitute a
    legal finding, legal advice, or determination that any offence occurred.
    All assessments require qualified human and/or legal review.
    """

    framework_id: str
    framework_name: str
    reason: str = Field(
        description="Factual basis from complaint/context that triggered this relevance signal."
    )
    trigger_count: int = Field(
        description="Number of relevance triggers matched.", ge=0
    )
    requires_human_legal_review: bool = True
    disclaimer: str = (
        "Potentially relevant — requires authorised human and/or legal review. "
        "This is NOT a legal determination."
    )


class IndiaContextAssessment(BaseModel):
    """Output of the deterministic India context layer.

    All fields describe POTENTIAL relevance only, not confirmed legal status.
    """

    potential_frameworks: list[PotentialFrameworkRelevance] = Field(
        default_factory=list
    )
    sc_st_context_detected: bool = False
    minority_context_detected: bool = False
    nalsa_referral_relevant: bool = False
    assessment_note: str = ""
    requires_human_legal_review: bool = True
    disclaimer: str = (
        "India contextual assessment is advisory only. "
        "All legal framework relevance requires authorised human and legal review. "
        "SENTRA does not make legal determinations."
    )


# ---------------------------------------------------------------------------
# Main assessor
# ---------------------------------------------------------------------------


class IndiaContextLayer:
    """Deterministic India legal/contextual relevance assessor.

    Usage:
        layer = IndiaContextLayer()
        india_ctx = layer.assess(structured_context, llm_output)
    """

    def assess(
        self,
        structured_context: StructuredContextInput | None,
        llm_output: LLMAssessmentOutput | None = None,
    ) -> IndiaContextAssessment:
        """Assess India-specific legal/contextual relevance.

        Args:
            structured_context: The structured intake context form fields.
            llm_output:         Optional LLM output for additional context signals.

        Returns:
            IndiaContextAssessment with potential framework relevance indicators.
        """
        if structured_context is None:
            return IndiaContextAssessment(
                assessment_note=(
                    "No structured context provided — legal framework relevance "
                    "cannot be assessed without self-reported identity and incident details."
                )
            )

        sc = structured_context
        ctx = llm_output.context if llm_output else None

        # Collect identity facts (self-reported only)
        identity_is_sc = sc.social_identity_context in (
            SocialIdentityContext.SC,
            SocialIdentityContext.ST,
            SocialIdentityContext.SC_ST,
        )
        identity_is_st = sc.social_identity_context in (
            SocialIdentityContext.ST,
            SocialIdentityContext.SC_ST,
        )
        identity_is_minority = sc.minority_community_context not in (
            MinorityCommunityContext.UNKNOWN,
            MinorityCommunityContext.NOT_APPLICABLE,
            MinorityCommunityContext.PREFER_NOT_TO_SAY,
        )
        identity_unknown = sc.social_identity_context in (
            SocialIdentityContext.UNKNOWN,
            SocialIdentityContext.PREFER_NOT_TO_SAY,
        )

        # Collect incident facts
        incident_types = set(sc.incident_type)
        atrocity_incident_types = {
            IncidentType.DISCRIMINATION,
            IncidentType.SOCIAL_EXCLUSION_BOYCOTT,
            IncidentType.DENIAL_OF_ACCESS,
            IncidentType.PHYSICAL_VIOLENCE,
            IncidentType.THREAT_INTIMIDATION,
            IncidentType.VERBAL_ABUSE,
            IncidentType.LAND_PROPERTY,
        }
        civil_rights_types = {
            IncidentType.DENIAL_OF_ACCESS,
            IncidentType.DISCRIMINATION,
            IncidentType.SOCIAL_EXCLUSION_BOYCOTT,
        }
        minority_relevant_types = {
            IncidentType.DISCRIMINATION,
            IncidentType.DENIAL_OF_ACCESS,
            IncidentType.SOCIAL_EXCLUSION_BOYCOTT,
            IncidentType.PHYSICAL_VIOLENCE,
            IncidentType.THREAT_INTIMIDATION,
            IncidentType.VERBAL_ABUSE,
        }

        has_atrocity_incident = bool(incident_types & atrocity_incident_types)
        has_civil_rights_incident = bool(incident_types & civil_rights_types)
        has_minority_incident = bool(incident_types & minority_relevant_types)

        # Legal aid relevance (NALSA) — independent of identity
        needs_legal_aid = (
            sc.legal_assistance_needed is True
            or (sc.fir_filed is False and sc.police_contacted is True)
        )

        # Assess framework relevance
        relevant_frameworks: list[PotentialFrameworkRelevance] = []

        # ── SC/ST (Prevention of Atrocities) Act, 1989 ──────────────────────
        if identity_is_sc and has_atrocity_incident and not identity_unknown:
            fw = LEGAL_FRAMEWORKS.get("sc_st_poa_1989")
            if fw:
                triggers = _count_triggers(fw, incident_types, sc, ctx)
                if triggers > 0:
                    relevant_frameworks.append(
                        PotentialFrameworkRelevance(
                            framework_id=fw.framework_id,
                            framework_name=fw.name,
                            reason=(
                                f"Self-reported SC/ST identity combined with reported "
                                f"incident type(s): "
                                f"{', '.join(t.value for t in incident_types & atrocity_incident_types)}. "
                                "Requires human and legal review."
                            ),
                            trigger_count=triggers,
                        )
                    )

        # ── Protection of Civil Rights Act, 1955 ─────────────────────────────
        if identity_is_sc and has_civil_rights_incident and not identity_unknown:
            fw = LEGAL_FRAMEWORKS.get("pcr_act_1955")
            if fw:
                triggers = _count_triggers(fw, incident_types, sc, ctx)
                if triggers > 0:
                    relevant_frameworks.append(
                        PotentialFrameworkRelevance(
                            framework_id=fw.framework_id,
                            framework_name=fw.name,
                            reason=(
                                "Self-reported SC/ST identity combined with reported "
                                "denial of access, discrimination, or social exclusion. "
                                "Requires human and legal review."
                            ),
                            trigger_count=triggers,
                        )
                    )

        # ── National Commission for Minorities ───────────────────────────────
        if identity_is_minority and has_minority_incident:
            fw = LEGAL_FRAMEWORKS.get("ncm_minorities")
            if fw:
                community = sc.minority_community_context.value
                relevant_frameworks.append(
                    PotentialFrameworkRelevance(
                        framework_id=fw.framework_id,
                        framework_name=fw.name,
                        reason=(
                            f"Self-reported minority community ({community}) combined with "
                            "reported discrimination or community-targeted incident. "
                            "NCM referral may be relevant. Requires human review."
                        ),
                        trigger_count=1,
                    )
                )

        # ── NALSA (Legal Aid) ─────────────────────────────────────────────────
        if needs_legal_aid:
            fw = LEGAL_FRAMEWORKS.get("nalsa_legal_aid")
            if fw:
                relevant_frameworks.append(
                    PotentialFrameworkRelevance(
                        framework_id=fw.framework_id,
                        framework_name=fw.name,
                        reason=(
                            "Legal assistance indicated as needed or FIR not yet filed. "
                            "NALSA free legal aid may be available."
                        ),
                        trigger_count=1,
                    )
                )

        # Build note
        if not relevant_frameworks:
            note = (
                "No specific legal framework relevance detected based on available "
                "structured context. This does not exclude relevance — human reviewer "
                "should assess based on full complaint details."
            )
        else:
            framework_names = [f.framework_name for f in relevant_frameworks]
            note = (
                f"{len(relevant_frameworks)} potentially relevant legal framework(s) "
                f"identified for human review: {'; '.join(framework_names)}. "
                "These are screening indicators only — not legal conclusions."
            )

        return IndiaContextAssessment(
            potential_frameworks=relevant_frameworks,
            sc_st_context_detected=identity_is_sc and not identity_unknown,
            minority_context_detected=identity_is_minority,
            nalsa_referral_relevant=needs_legal_aid,
            assessment_note=note,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_triggers(
    framework: LegalFrameworkReference,
    incident_types: set[IncidentType],
    sc: StructuredContextInput,
    ctx: object | None,
) -> int:
    """Count how many of the framework's factual triggers are matched.

    Args:
        framework:      The legal framework reference.
        incident_types: Set of incident types from structured context.
        sc:             The full structured context.
        ctx:            LLM context extraction (optional).

    Returns:
        Number of triggers matched (0 means no relevance).
    """
    count = 0
    for trigger_key in framework.factual_trigger_keys:
        if trigger_key == "has_atrocity_incident_type":
            if incident_types & {
                IncidentType.DISCRIMINATION,
                IncidentType.SOCIAL_EXCLUSION_BOYCOTT,
                IncidentType.PHYSICAL_VIOLENCE,
                IncidentType.THREAT_INTIMIDATION,
                IncidentType.VERBAL_ABUSE,
                IncidentType.DENIAL_OF_ACCESS,
                IncidentType.LAND_PROPERTY,
            }:
                count += 1
        elif trigger_key == "denial_of_access":
            if IncidentType.DENIAL_OF_ACCESS in incident_types:
                count += 1
        elif trigger_key == "social_exclusion":
            if IncidentType.SOCIAL_EXCLUSION_BOYCOTT in incident_types:
                count += 1
        elif trigger_key == "discrimination":
            if IncidentType.DISCRIMINATION in incident_types:
                count += 1
        elif trigger_key == "physical_violence":
            if IncidentType.PHYSICAL_VIOLENCE in incident_types:
                count += 1
        elif trigger_key == "police_contacted":
            if sc.police_contacted is True:
                count += 1
        elif trigger_key == "fir_not_filed":
            if sc.fir_filed is False:
                count += 1
    return count
