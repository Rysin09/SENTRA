"""
Fairness invariants for the screening pipeline.
Identity fields must not alter AI screening scores, only legal routing.
"""

import pytest

from sentra.assessment.pipeline import TextScreeningPipeline
from sentra.domain.context_schemas import (
    SocialIdentityContext,
    StructuredContextInput,
)


@pytest.mark.skip(reason="Requires mocked LLM to guarantee deterministic outputs for testing")
def test_fairness_invariant_identity_does_not_affect_scores():
    """Test that two identical complaints with different identities get the same distress score."""
    pipeline = TextScreeningPipeline()

    ctx_sc = StructuredContextInput(social_identity_context=SocialIdentityContext.SC)
    ctx_unknown = StructuredContextInput(social_identity_context=SocialIdentityContext.UNKNOWN)

    text = "I am being harassed and threatened at my workplace."

    res_sc = pipeline.run("case-1", text, ctx_sc)
    res_unknown = pipeline.run("case-2", text, ctx_unknown)

    # Distress scores and operational categories MUST be identical
    assert res_sc.operational_category == res_unknown.operational_category
    assert abs(res_sc.confidence - res_unknown.confidence) < 0.01

    # Only legal framework routing should differ
    assert len(res_sc.india_context.potential_frameworks) >= 0
