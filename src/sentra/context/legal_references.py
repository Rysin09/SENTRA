"""
Versioned legal framework reference configuration for SENTRA.

PURPOSE:
  Provides factual trigger conditions for each legal/contextual framework
  that may be potentially relevant to NHAA/SENTRA complaints in India.

CRITICAL DISCLAIMERS:
  - These references are SCREENING INDICATORS only.
  - They do NOT constitute legal advice or legal determinations.
  - All require authorised human and/or qualified legal review.
  - Trigger conditions are simplified operational summaries for screening.
  - Full legal text should always be consulted by qualified legal professionals.

SOURCE GOVERNANCE:
  All legal references sourced from official Indian government sources.
  URLs verified at time of configuration. URL and text accuracy must be
  verified before production use.

VERSIONING:
  version_date: ISO date of last review and update.
  Increment when legal text changes (e.g., amendment notification).

Frameworks included:
  1. SC/ST (Prevention of Atrocities) Act, 1989
  2. SC/ST (Prevention of Atrocities) Amendment Act, 2015 (effective 2016)
  3. Protection of Civil Rights Act, 1955
  4. National Commission for Minorities Act, 1992
  5. NALSA (National Legal Services Authority) — free legal aid
  6. NHAA 14566 helpline reference
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LegalFrameworkReference:
    """Immutable configuration record for a single legal framework.

    Attributes:
        framework_id:        Unique stable identifier (snake_case).
        name:                Human-readable name for UI display.
        official_source:     Name of official issuing authority.
        source_url:          URL to official text (verified at version_date).
        version_date:        ISO date this configuration was last reviewed.
        scope:               One-line scope description.
        factual_trigger_keys: Keys checked by IndiaContextLayer._count_triggers().
        requires_human_legal_review: Always True — do not change.
        disclaimer:          Standard disclaimer for all outputs.
    """

    framework_id: str
    name: str
    official_source: str
    source_url: str
    version_date: str
    scope: str
    factual_trigger_keys: tuple[str, ...]
    requires_human_legal_review: bool = True
    disclaimer: str = (
        "Potentially relevant — requires authorised human and/or qualified legal review. "
        "This is NOT a legal determination."
    )


# ---------------------------------------------------------------------------
# Framework definitions
# ---------------------------------------------------------------------------

LEGAL_FRAMEWORKS: dict[str, LegalFrameworkReference] = {

    "sc_st_poa_1989": LegalFrameworkReference(
        framework_id="sc_st_poa_1989",
        name="SC/ST (Prevention of Atrocities) Act, 1989",
        official_source="Ministry of Social Justice and Empowerment, Government of India",
        source_url="https://www.indiacode.nic.in/handle/123456789/1920",
        version_date="2024-01-01",
        scope=(
            "Protects Scheduled Castes and Scheduled Tribes from offences of "
            "atrocity, humiliation, and denial of rights. Provides for special "
            "courts and relief measures."
        ),
        factual_trigger_keys=(
            "has_atrocity_incident_type",
            "social_exclusion",
            "discrimination",
            "physical_violence",
            "denial_of_access",
        ),
    ),

    "sc_st_poa_amendment_2015": LegalFrameworkReference(
        framework_id="sc_st_poa_amendment_2015",
        name="SC/ST (Prevention of Atrocities) Amendment Act, 2015/2018",
        official_source="Ministry of Social Justice and Empowerment, Government of India",
        source_url="https://www.indiacode.nic.in/handle/123456789/1920",
        version_date="2024-01-01",
        scope=(
            "Amends the 1989 Act — expands definition of atrocity offences, "
            "provides for preliminary inquiry, and strengthens relief provisions."
        ),
        factual_trigger_keys=(
            "has_atrocity_incident_type",
            "social_exclusion",
            "discrimination",
        ),
    ),

    "pcr_act_1955": LegalFrameworkReference(
        framework_id="pcr_act_1955",
        name="Protection of Civil Rights Act, 1955",
        official_source="Ministry of Social Justice and Empowerment, Government of India",
        source_url="https://www.indiacode.nic.in/handle/123456789/2052",
        version_date="2024-01-01",
        scope=(
            "Punishes the enforcement of any disability arising out of untouchability. "
            "Covers denial of access to places of public worship, shops, hospitals, "
            "water sources, or other public utilities based on untouchability."
        ),
        factual_trigger_keys=(
            "denial_of_access",
            "social_exclusion",
            "discrimination",
        ),
    ),

    "ncm_minorities": LegalFrameworkReference(
        framework_id="ncm_minorities",
        name="National Commission for Minorities Act, 1992 — NCM Referral",
        official_source="National Commission for Minorities, Government of India",
        source_url="https://ncm.nic.in/",
        version_date="2024-01-01",
        scope=(
            "The National Commission for Minorities (NCM) addresses grievances of "
            "notified minority communities: Muslim, Christian, Sikh, Buddhist, "
            "Parsi/Zoroastrian, Jain. Handles complaints of discrimination, denial "
            "of rights, and minority rights violations."
        ),
        factual_trigger_keys=(
            "discrimination",
            "denial_of_access",
            "social_exclusion",
            "physical_violence",
        ),
    ),

    "nalsa_legal_aid": LegalFrameworkReference(
        framework_id="nalsa_legal_aid",
        name="NALSA — Free Legal Aid (Legal Services Authorities Act, 1987)",
        official_source="National Legal Services Authority, Government of India",
        source_url="https://nalsa.gov.in/",
        version_date="2024-01-01",
        scope=(
            "NALSA provides free legal services to eligible persons including "
            "SC/ST members, victims of trafficking, women, persons with disabilities, "
            "and persons with annual income below the prescribed limit. "
            "Includes legal advice, court representation, and lok adalat services."
        ),
        factual_trigger_keys=(
            "fir_not_filed",
            "police_contacted",
        ),
    ),

    "nhaa_14566": LegalFrameworkReference(
        framework_id="nhaa_14566",
        name="NHAA 14566 — National Human Atrocities Alert Helpline",
        official_source="Ministry of Social Justice and Empowerment, Government of India",
        source_url="https://socialjustice.gov.in/",
        version_date="2024-01-01",
        scope=(
            "National 24/7 helpline for reporting atrocities against SC/ST persons "
            "and other vulnerable groups. Toll-free: 14566. "
            "Provides immediate referral to district authorities and support agencies."
        ),
        factual_trigger_keys=(
            "has_atrocity_incident_type",
        ),
    ),
}
