"""
Screening Results display component — Phase 2.

Reusable Streamlit component that renders an AssessmentResult in a
structured, safe, and clear format.

Security:
  - No complaint text is ever passed to or displayed by this component.
  - Indicator lists shown are the extracted keyword names, not text snippets.
  - The disclaimer is always displayed prominently.

IMPORTANT:
  - This display is operational screening output ONLY.
  - It is NOT a medical, psychiatric, or legal assessment.
  - All results require human review before any action.
"""

from __future__ import annotations

import streamlit as st

from sentra.domain.enums import OperationalCategory
from sentra.domain.models import AssessmentDimension, AssessmentResult

# ── Category styling ──────────────────────────────────────────────────────────

_CATEGORY_CONFIG: dict[OperationalCategory, dict] = {
    OperationalCategory.CRITICAL: {
        "emoji": "🔴",
        "label": "CRITICAL",
        "colour": "#dc2626",
        "bg": "#fef2f2",
        "border": "#fca5a5",
        "st_type": "error",
        "description": "Immediate human review required.",
    },
    OperationalCategory.HIGH: {
        "emoji": "🟠",
        "label": "HIGH",
        "colour": "#ea580c",
        "bg": "#fff7ed",
        "border": "#fed7aa",
        "st_type": "warning",
        "description": "Priority human review required.",
    },
    OperationalCategory.MODERATE: {
        "emoji": "🟡",
        "label": "MODERATE",
        "colour": "#ca8a04",
        "bg": "#fefce8",
        "border": "#fde68a",
        "st_type": "warning",
        "description": "Human review recommended.",
    },
    OperationalCategory.LOW: {
        "emoji": "🟢",
        "label": "LOW",
        "colour": "#16a34a",
        "bg": "#f0fdf4",
        "border": "#bbf7d0",
        "st_type": "success",
        "description": "Routine review applies.",
    },
    OperationalCategory.INSUFFICIENT_DATA: {
        "emoji": "⚪",
        "label": "INSUFFICIENT DATA",
        "colour": "#6b7280",
        "bg": "#f9fafb",
        "border": "#d1d5db",
        "st_type": "info",
        "description": "Insufficient text — Human Review Required.",
    },
}

_DIMENSION_LABELS: dict[str, str] = {
    "acute_distress": "Acute Distress",
    "fear_threat_perception": "Fear / Threat Perception",
    "anxiety_indicators": "Anxiety Indicators",
    "trauma_related_indicators": "Trauma-Related Indicators",
    "immediate_vulnerability": "Immediate Vulnerability",
    "social_support_availability": "Social Support Availability",
    "urgency": "Urgency",
    "communication_difficulty": "Communication Difficulty",
}

# social_support is inverse — higher score = MORE support = LOWER risk
_INVERSE_DIMENSIONS: frozenset[str] = frozenset({"social_support_availability"})


def render_reviewer_result(result: AssessmentResult, *, compact: bool = False) -> None:
    """Render an AssessmentResult for the authorized reviewer dashboard.

    Args:
        result: The assessment to display.
        compact: If True, renders a condensed single-row summary.
                 If False, renders the full breakdown.
    """
    if compact:
        _render_compact(result)
    else:
        _render_full(result)


def render_complainant_acknowledgement(case_id: str) -> None:
    """Render a neutral, safe acknowledgement for the complainant post-submission.
    
    This explicitly hides all AI labels, screening dimensions, confidence scores,
    and operational categories to prevent distress or confusion.
    """
    st.success(
        f"✅ **Your complaint has been successfully submitted.**\n\n"
        f"**Case reference:** `{case_id}`\n\n"
        "Your submission has been securely recorded and routed for review. "
        "An authorized human officer will carefully review your case before any action is taken. "
        "Please keep your case reference number safe for future tracking."
    )
    st.info(
        "ℹ️ **What happens next?**\n"
        "The system has performed an initial automated check to assist our reviewers, "
        "but the final decision and next steps will always be determined by a human officer."
    )



# ── Full render ───────────────────────────────────────────────────────────────


def _render_full(result: AssessmentResult) -> None:
    """Render the complete assessment result panel."""
    cfg = _CATEGORY_CONFIG.get(result.operational_category, _CATEGORY_CONFIG[OperationalCategory.INSUFFICIENT_DATA])

    # ── Disclaimer (always first) ─────────────────────────────────────────
    st.info(
        "⚠️ **Operational Screening Output Only** — This is AI-assisted screening support. "
        "It does **not** constitute a medical diagnosis, psychiatric classification, "
        "or legal determination. All outputs require **authorized human review** before any action.",
    )

    # ── Category banner ───────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background:{cfg['bg']};
            border:2px solid {cfg['border']};
            border-radius:12px;
            padding:18px 24px;
            margin-bottom:16px;
        ">
            <div style="font-size:2rem;font-weight:800;color:{cfg['colour']};">
                {cfg['emoji']} {cfg['label']}
            </div>
            <div style="color:{cfg['colour']};font-size:0.95rem;margin-top:4px;">
                Operational Priority · {cfg['description']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Confidence + pipeline metadata ────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        confidence_pct = int(result.confidence * 100)
        st.metric("Screening Confidence", f"{confidence_pct}%")
    with col2:
        st.metric("Pipeline Version", result.pipeline_version)
    with col3:
        review_label = "🔴 Required" if result.human_review_required else "🟢 Routine"
        st.metric("Human Review", review_label)

    st.progress(result.confidence, text=f"Confidence: {confidence_pct}%")
    st.divider()

    # ── Human review alert ────────────────────────────────────────────────
    if result.human_review_required:
        if result.operational_category == OperationalCategory.CRITICAL:
            st.error(
                "🚨 **Immediate Human Review Required** — This case has been flagged at CRITICAL "
                "operational priority. An authorized officer must review this case urgently."
            )
        elif result.operational_category == OperationalCategory.HIGH:
            st.warning(
                "⚠️ **Priority Human Review Required** — This case requires prompt review by an "
                "authorized officer."
            )
        elif result.operational_category == OperationalCategory.INSUFFICIENT_DATA:
            st.info(
                "ℹ️ **Human Review Required** — Insufficient text was provided for AI screening. "
                "An officer should follow up to gather more information."
            )

    # ── Explanation ───────────────────────────────────────────────────────
    st.subheader("Screening Summary")
    st.write(result.explanation)
    st.divider()

    # ── Dimension breakdown ───────────────────────────────────────────────
    st.subheader("Dimension Breakdown")
    st.caption(
        "Each dimension reflects the presence of operational screening indicators in the text. "
        "**Social Support Availability** is an inverse dimension — higher score indicates more support present."
    )

    dims_by_name = {d.name: d for d in result.dimensions}

    # Sort: highest risk first (but social support last as it's inverse)
    ordered_dims = sorted(
        result.dimensions,
        key=lambda d: (d.name == "social_support_availability", -d.score),
    )

    for dim in ordered_dims:
        _render_dimension(dim)

    st.divider()

    # ── Modalities used ───────────────────────────────────────────────────
    if result.modalities_used:
        st.subheader("Modalities Processed")
        cols = st.columns(len(result.modalities_used))
        for i, mod in enumerate(result.modalities_used):
            with cols[i]:
                quality_emoji = {"GOOD": "🟢", "DEGRADED": "🟡", "FAILED": "🔴", "NOT_PROVIDED": "⚪"}.get(
                    mod.quality.value, "⚪"
                )
                st.metric(
                    mod.modality.value.title(),
                    f"{quality_emoji} {mod.quality.value}",
                )
                if mod.notes:
                    st.caption(mod.notes)

    # ── Assessment metadata ───────────────────────────────────────────────
    with st.expander("Assessment Metadata", expanded=False):
        meta_dict = {
            "case_id": str(result.case_id),
            "assessed_at": result.assessed_at.isoformat() if result.assessed_at else None,
            "pipeline_version": result.pipeline_version,
            "operational_category": result.operational_category.value,
            "confidence": result.confidence,
            "human_review_required": result.human_review_required,
            "safety_flags": len(result.safety_flags),
        }
        if hasattr(result, "extra_metadata") and result.extra_metadata:
            meta_dict["llm_metadata"] = result.extra_metadata

        st.json(meta_dict)


def _render_dimension(dim: AssessmentDimension) -> None:
    """Render a single dimension score row."""
    label = _DIMENSION_LABELS.get(dim.name, dim.name.replace("_", " ").title())
    is_inverse = dim.name in _INVERSE_DIMENSIONS

    # For inverse dimension, display "support available" level
    display_score = dim.score
    score_pct = int(display_score * 100)

    # Color code by score (for inverse: high score = good = green)
    if is_inverse:
        if display_score >= 0.5:
            bar_colour = "normal"
        else:
            bar_colour = "normal"
    else:
        bar_colour = "normal"

    col_label, col_bar, col_score, col_indicators = st.columns([3, 4, 1, 4])
    with col_label:
        inverse_note = " ↓ (inverse)" if is_inverse else ""
        st.markdown(f"**{label}**{inverse_note}")
    with col_bar:
        st.progress(display_score)
    with col_score:
        st.markdown(f"`{score_pct}%`")
    with col_indicators:
        if dim.supporting_indicators:
            indicators_str = ", ".join(f"`{ind}`" for ind in dim.supporting_indicators[:4])
            if len(dim.supporting_indicators) > 4:
                indicators_str += f" +{len(dim.supporting_indicators) - 4} more"
            st.caption(indicators_str)
        else:
            st.caption("—")


# ── Compact render ─────────────────────────────────────────────────────────────


def _render_compact(result: AssessmentResult) -> None:
    """Render a compact one-row summary (for dashboard tables)."""
    cfg = _CATEGORY_CONFIG.get(result.operational_category, _CATEGORY_CONFIG[OperationalCategory.INSUFFICIENT_DATA])
    confidence_pct = int(result.confidence * 100)
    review_icon = "🔴" if result.human_review_required else "🟢"

    col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
    with col1:
        st.markdown(
            f"<span style='color:{cfg['colour']};font-weight:700;'>{cfg['emoji']} {cfg['label']}</span>",
            unsafe_allow_html=True,
        )
    with col2:
        st.caption(f"Confidence: {confidence_pct}%")
    with col3:
        st.caption(f"Review: {review_icon}")
    with col4:
        st.caption(f"v{result.pipeline_version}")
