"""
Case History page — Phase 1.

Shows a list of recent submitted cases (safe read-model — no complaint text).
Full assessment/review details will be added in Phase 6.
"""

from __future__ import annotations

import streamlit as st

from sentra.services.case_service import CaseService


def render() -> None:
    """Render the Case History page."""
    st.title("📋 Case History")
    st.caption("Authorized access only · Records are audit-logged.")
    st.divider()

    st.info(
        "Showing submitted cases. Complaint text is not displayed here. "
        "Use the **Reviewer Dashboard** to view full AI assessment results and conduct reviews.",
        icon="ℹ️",
    )

    with st.spinner("Loading cases…"):
        try:
            service = CaseService()
            cases = service.list_recent_cases(limit=50)
        except Exception:  # noqa: BLE001
            st.error(
                "Could not load cases. Check the database connection.",
            )
            return

    if not cases:
        st.markdown("_No cases submitted yet._")
        return

    st.markdown(f"**{len(cases)} most recent case(s)**")
    st.divider()

    for case in cases:
        with st.container():
            cols = st.columns([3, 2, 1, 1])
            with cols[0]:
                st.markdown("**Case ID**")
                st.code(str(case.case_id), language=None)
            with cols[1]:
                st.markdown("**Submitted**")
                st.caption(
                    case.submitted_at.strftime("%Y-%m-%d %H:%M UTC")
                    if case.submitted_at.tzinfo
                    else case.submitted_at.strftime("%Y-%m-%d %H:%M")
                )
            with cols[2]:
                st.markdown("**Audio**")
                st.caption("✓ Yes" if case.has_audio else "— No")
            with cols[3]:
                st.markdown("**Status**")
                st.caption("🔵 Pending Review")
            st.divider()

    st.caption("**Phase 4 — Reviewer Workflow and UI Separation Active**")
