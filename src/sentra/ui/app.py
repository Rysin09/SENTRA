"""
SENTRA Streamlit application shell — Phase 0.

Provides the multi-page navigation skeleton. Individual pages are imported
from ``sentra.ui.pages``. Real pipeline logic is wired in later phases.

Run with:
    streamlit run src/sentra/main.py
"""

from __future__ import annotations

import streamlit as st

from sentra.config.settings import get_settings
from sentra.database.session import check_database_connection
from sentra.ui.pages import case_history, case_intake, reviewer_dashboard


def _configure_page() -> None:
    """Apply global Streamlit page configuration."""
    st.set_page_config(
        page_title="SENTRA — Screening Support",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": (
                "**SENTRA** v0.2.0 — AI-Assisted Multimodal Distress & Vulnerability Screening\n\n"
                "SIH 2026 — SIH26093 · Phase 2: Text Screening\n\n"
                "_AI assists. Human decides. Not a diagnosis._"
            ),
        },
    )


def _sidebar() -> str:
    """Render the sidebar navigation and return the selected page name."""
    st.sidebar.markdown("### 🛡️ SENTRA")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "Go to",
        options=["Case Intake", "Reviewer Dashboard", "Case History"],
        label_visibility="collapsed",
    )

    settings = get_settings()
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Environment: `{settings.sentra_env}`")
    st.sidebar.caption("Version: 0.2.0 — Phase 2 · Text Screening")

    # Database health indicator
    db_ok = check_database_connection()
    db_label = "🟢 Database connected" if db_ok else "🔴 Database unavailable"
    st.sidebar.caption(db_label)

    st.sidebar.markdown("---")
    st.sidebar.info(
        "⚠️ **AI assists. Human decides.**\n\n"
        "This tool provides screening support only. "
        "All assessments require authorized human review.",
        icon=None,
    )

    return str(page)


def run_app() -> None:
    """Configure and run the SENTRA Streamlit application."""
    _configure_page()
    page = _sidebar()

    if page == "Case Intake":
        case_intake.render()
    elif page == "Reviewer Dashboard":
        reviewer_dashboard.render()
    elif page == "Case History":
        case_history.render()
    else:
        st.error("Unknown page selected.")
