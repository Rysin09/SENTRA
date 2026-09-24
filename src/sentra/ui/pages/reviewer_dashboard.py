"""
Reviewer Dashboard page — Phase 3.

Full reviewer workflow:
1. PIN authentication gate.
2. List recent AI screening assessments.
3. Show raw audited complaint text.
4. Show AI screening output.
5. Record human review decision and save to database.
"""

from __future__ import annotations

import os

import streamlit as st

from sentra.domain.enums import OperationalCategory
from sentra.services.case_service import CaseService
from sentra.services.review_service import ReviewService
from sentra.ui.pages import screening_results


def render() -> None:
    """Render the Reviewer Dashboard page."""
    st.title("👤 Reviewer Dashboard")
    st.caption("Authorized personnel only · AI assists. Human decides.")
    st.divider()

    # ── Authentication Gate ──────────────────────────────────────────────────
    pin_required = os.environ.get("REVIEWER_PIN", "1234")
    if "reviewer_authenticated" not in st.session_state:
        st.session_state["reviewer_authenticated"] = False

    if not st.session_state["reviewer_authenticated"]:
        with st.form("auth_form"):
            st.warning("🔒 **Authentication Required**")
            st.info("Enter the reviewer PIN to access sensitive case data.")
            pin = st.text_input("Reviewer PIN", type="password")
            submitted = st.form_submit_button("Log In")
            if submitted:
                if pin == pin_required:
                    st.session_state["reviewer_authenticated"] = True
                    st.session_state["reviewer_id"] = "reviewer_01"  # Stub for MVP
                    st.rerun()
                else:
                    st.error("Invalid PIN.")
        return

    # Authenticated content
    st.sidebar.success(f"Logged in as: `{st.session_state['reviewer_id']}`")
    if st.sidebar.button("Log Out"):
        st.session_state["reviewer_authenticated"] = False
        del st.session_state["reviewer_id"]
        st.rerun()

    st.info(
        "⚠️ **Operational Screening Outputs Only** — The assessments below are "
        "AI-assisted screening indicators. They are **not** medical diagnoses, "
        "psychiatric classifications, or legal determinations. Each case requires "
        "authorized human review before any action is taken.",
    )

    st.divider()
    st.subheader("Recent Assessments")

    # Load recent assessments
    case_service = CaseService()
    try:
        assessments = case_service.list_recent_assessments(limit=50)
    except Exception as exc:  # noqa: BLE001
        st.error("Failed to load assessments. Please try again.")
        st.caption(f"Error type: {type(exc).__name__}")
        return

    if not assessments:
        st.info(
            "No assessments found yet. Submit a case via **Case Intake** to generate "
            "the first AI screening result."
        )
        return

    # Filter controls
    col_filter, col_sort = st.columns([3, 2])
    with col_filter:
        show_only_review = st.checkbox("Show only cases requiring human review", value=True)
    with col_sort:
        sort_by = st.selectbox("Sort by", ["Highest category", "Newest first"], index=0)

    # Review status cache to determine what to show
    review_service = ReviewService()

    # We will filter visually, but keep all in memory for sorting
    display_assessments = []
    for a in assessments:
        rev = review_service.get_latest_review(a.case_id)
        if show_only_review and (not a.human_review_required or rev is not None):
            continue
        display_assessments.append((a, rev))

    _CATEGORY_ORDER = {
        "CRITICAL": 0, "HIGH": 1, "MODERATE": 2,
        "LOW": 3, "INSUFFICIENT_DATA": 4,
    }

    if sort_by == "Highest category":
        display_assessments = sorted(
            display_assessments,
            key=lambda item: _CATEGORY_ORDER.get(item[0].operational_category.value, 99),
        )
    else:
        display_assessments = sorted(
            display_assessments,
            key=lambda item: item[0].assessed_at,
            reverse=True,
        )

    # Show summary count
    st.caption(f"Showing **{len(display_assessments)}** assessments.")
    st.divider()

    if not display_assessments:
        st.success("All caught up! No cases match the current filter.")
        return

    # Render each assessment as an expandable card
    for i, (assessment, review_record) in enumerate(display_assessments):
        _render_assessment_card(assessment, review_record, case_service, review_service, index=i)

    st.markdown("---")
    st.caption("**Phase 3 — Reviewer Workflow Active**")


def _render_assessment_card(
    assessment: object,  # type: ignore[type-arg]
    review_record: object,  # type: ignore[type-arg]
    case_service: CaseService,
    review_service: ReviewService,
    *,
    index: int
) -> None:
    """Render a single assessment as a collapsible card with a review form."""
    _EMOJI = {
        "CRITICAL": "🔴",
        "HIGH": "🟠",
        "MODERATE": "🟡",
        "LOW": "🟢",
        "INSUFFICIENT_DATA": "⚪",
    }

    cat_val = assessment.operational_category.value
    emoji = _EMOJI.get(cat_val, "⚪")
    confidence_pct = int(assessment.confidence * 100)

    if review_record:
        review_icon = "✅ Reviewed"
    else:
        review_icon = "🔴 Review Required" if assessment.human_review_required else "🟢 Routine"

    case_short = str(assessment.case_id)[:8]
    assessed_str = (
        assessment.assessed_at.strftime("%Y-%m-%d %H:%M UTC")
        if assessment.assessed_at
        else "Unknown"
    )

    title = f"{emoji} **{cat_val}** · Case `{case_short}…` · {confidence_pct}% confidence · {review_icon}"

    with st.expander(title, expanded=(index == 0)):
        st.caption(f"Case ID: `{assessment.case_id}` · Assessed: {assessed_str} · Pipeline: v{assessment.pipeline_version}")

        # 1. Show Original Complaint Text (Audited Path)
        st.markdown("### 📝 Original Complaint")
        complaint_text = case_service.get_complaint_text(assessment.case_id)
        if complaint_text:
            st.info(complaint_text)
        else:
            st.error("Complaint text not found.")

        # 2. Show AI Screening Results
        st.markdown("### 🤖 AI Screening")
        screening_results.render_reviewer_result(assessment, compact=False)

        st.divider()

        # 3. Human Review Form
        st.markdown("### 👨‍⚖️ Human Decision")

        if review_record:
            st.success(f"Review completed by `{review_record.reviewer_id}` on {review_record.reviewed_at.strftime('%Y-%m-%d %H:%M UTC')}")
            st.write(f"**Final Category:** `{review_record.reviewer_category}`")
            if review_record.overridden:
                st.warning(f"⚠️ **Override Applied:** AI recommended `{review_record.ai_category}`")
            if review_record.reviewer_note:
                st.write(f"**Notes:** {review_record.reviewer_note}")
        else:
            with st.form(f"review_form_{assessment.case_id}"):
                final_cat_str = st.selectbox(
                    "Final Operational Category",
                    options=["CRITICAL", "HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"],
                    index=["CRITICAL", "HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"].index(cat_val),
                )
                notes = st.text_area("Reviewer Notes / Rationale (required if overriding)")

                submitted = st.form_submit_button("Save Review Decision", type="primary")

                if submitted:
                    final_cat = OperationalCategory(final_cat_str)
                    is_override = final_cat != assessment.operational_category
                    if is_override and not notes.strip():
                        st.error("⚠️ Notes are required when overriding the AI's recommended category.")
                    else:
                        review_service.submit_review(
                            case_id=assessment.case_id,
                            reviewer_id=st.session_state["reviewer_id"],
                            reviewer_category=final_cat,
                            reviewer_note=notes.strip() if notes.strip() else None,
                        )
                        st.success("Review saved successfully!")
                        st.rerun()
