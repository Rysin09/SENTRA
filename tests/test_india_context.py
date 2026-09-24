"""
Tests for the IndiaContextLayer mapping rules.
"""

import pytest

from sentra.context.india_context_layer import IndiaContextLayer
from sentra.domain.context_schemas import (
    IncidentType,
    MinorityCommunityContext,
    SocialIdentityContext,
    StructuredContextInput,
)


@pytest.fixture
def context_layer():
    return IndiaContextLayer()

def test_sc_st_poa_mapped(context_layer):
    """Test that SC/ST PoA Act is suggested when identity and incident match."""
    ctx = StructuredContextInput(
        social_identity_context=SocialIdentityContext.SC,
        incident_type=[IncidentType.VERBAL_ABUSE, IncidentType.PHYSICAL_VIOLENCE],
    )
    result = context_layer.assess(
        structured_context=ctx,
        llm_output=None,
    )
    assert any("SC/ST (Prevention of Atrocities) Act" in frame.framework_name for frame in result.potential_frameworks)
    assert result.requires_human_legal_review is True

def test_ncm_mapped(context_layer):
    """Test that NCM is suggested for religious minorities facing discrimination."""
    ctx = StructuredContextInput(
        minority_community_context=MinorityCommunityContext.MUSLIM,
        incident_type=[IncidentType.DISCRIMINATION],
    )
    result = context_layer.assess(
        structured_context=ctx,
        llm_output=None,
    )
    assert any("National Commission for Minorities" in frame.framework_name for frame in result.potential_frameworks)
    assert result.requires_human_legal_review is True

def test_no_framework_inferred_if_unknown(context_layer):
    """Test that identity is not inferred, and no frameworks are suggested if not applicable."""
    ctx = StructuredContextInput(
        social_identity_context=SocialIdentityContext.UNKNOWN,
        minority_community_context=MinorityCommunityContext.UNKNOWN,
        incident_type=[IncidentType.ONLINE_HARASSMENT],
    )
    result = context_layer.assess(
        structured_context=ctx,
        llm_output=None,
    )
    assert len(result.potential_frameworks) == 0
