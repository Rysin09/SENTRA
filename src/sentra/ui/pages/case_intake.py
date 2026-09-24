"""
Case Intake page — Phase 2.

Implements the full intake and screening workflow:
  1. Consent acknowledgement (hard gate).
  2. Complaint text input and character-level validation.
  3. Optional audio file upload (stored filename only; processed in Phase 3).
  4. Operator context notes.
  5. Submit → persist case → run NLP screening → display results.

Security:
  - Complaint text is never logged or echoed back verbatim in any output.
  - User text is treated as untrusted throughout.
  - Submission fails safely and does NOT fabricate a case_id on error.
  - Screening result is displayed but complaint text is NEVER shown.
"""

from __future__ import annotations

import logging
import uuid

import streamlit as st
from pydantic import ValidationError

from sentra.domain.context_schemas import (
    IncidentType,
    MinorityCommunityContext,
    SocialIdentityContext,
    StructuredContextInput,
)
from sentra.domain.schemas import CaseSubmission
from sentra.services.case_service import CaseService
from sentra.ui.pages import screening_results

logger = logging.getLogger(__name__)

_MIN_CHARS = 10
_MAX_CHARS = 5000


def _reset_form() -> None:
    """Clear all intake form keys from Streamlit session state."""
    for key in ["intake_consent", "intake_text", "intake_audio", "intake_context"]:
        if key in st.session_state:
            del st.session_state[key]


def render() -> None:
    """Render the Case Intake page."""
    st.title("🛡️ SENTRA — Case Intake")
    st.caption(
        "AI-assisted screening support · SIH 2026 · _AI assists. Human decides._"
    )
    st.divider()

    # ── Success + screening results (shown after a successful submission) ──
    if "last_case_id" in st.session_state and "last_assessment" in st.session_state:
        _render_post_submission_receipt()
        return

    # ── 1. Consent ────────────────────────────────────────────────────────────
    st.subheader("1. Consent")
    st.info(
        "Before proceeding, the complainant must provide **explicit informed consent** "
        "for AI-assisted screening of their submission.\n\n"
        "This system:\n"
        "- Does **not** diagnose medical or psychiatric conditions.\n"
        "- Does **not** determine legal guilt or victim status.\n"
        "- Does **not** take autonomous legal or police action.\n"
        "- Requires review by an **authorized human officer** before any action.",
    )
    consent = st.checkbox(
        "I understand that this submission will be processed by an AI screening "
        "system and reviewed by an authorized human officer.",
        key="intake_consent",
    )

    st.divider()

    # ── 2. Complaint text ─────────────────────────────────────────────────────
    st.subheader("2. Complaint / Statement")
    complaint_text: str = st.text_area(
        "Please describe the situation in your own words.",
        height=220,
        max_chars=_MAX_CHARS,
        placeholder="Describe the situation here…",
        key="intake_text",
    )
    char_count = len(complaint_text.strip())
    colour = "green" if char_count >= _MIN_CHARS else "orange"
    st.markdown(
        f":{colour}[{char_count} / {_MAX_CHARS} characters "
        f"(minimum {_MIN_CHARS})]"
    )

    st.divider()

    # ── 3. Audio upload (optional — Phase 3 will process it) ──────────────────
    st.subheader("3. Voice Recording (Optional)")
    st.caption(
        "A voice recording can be uploaded here. "
        "Audio processing will be available from Phase 3 onward. "
        "Supported formats: WAV · MP3 · OGG · FLAC · M4A · Maximum 50 MB"
    )
    audio_file = st.file_uploader(
        "Upload an audio recording (optional)",
        type=["wav", "mp3", "ogg", "flac", "m4a"],
        key="intake_audio",
    )
    audio_filename: str | None = None
    if audio_file is not None:
        audio_filename = audio_file.name
        st.audio(audio_file)
        st.caption(f"File: `{audio_filename}` · {audio_file.size / 1024:.1f} KB")

    st.divider()

    # ── 4. Operator Context Form (not shown to complainant) ───────────────────
    st.subheader("4. Operator Context (Optional)")
    st.caption(
        "For authorized operator use only. Information collected here is used "
        "only to assist in identifying potential legal framework relevance and routing. "
        "Identity fields **never** alter the text screening confidence or severity scores."
    )

    with st.expander("📝 Fill Structured Context (Operator Use Only)", expanded=False):
        st.markdown("**Identity (Self-reported only)**")
        social_id = st.selectbox(
            "Scheduled Caste / Scheduled Tribe status",
            options=[e.value for e in SocialIdentityContext],
            index=list(SocialIdentityContext).index(SocialIdentityContext.UNKNOWN),
            help="Do not guess. Only enter if explicitly stated by the complainant."
        )
        minority_id = st.selectbox(
            "Religious Minority Community",
            options=[e.value for e in MinorityCommunityContext],
            index=list(MinorityCommunityContext).index(MinorityCommunityContext.UNKNOWN),
            help="Do not guess. Only enter if explicitly stated by the complainant."
        )

        st.markdown("**Incident Details**")
        incident_types = st.multiselect(
            "Incident Type(s)",
            options=[e.value for e in IncidentType],
        )

        st.markdown("**Current Safety & Support**")
        col_safe1, col_safe2 = st.columns(2)
        with col_safe1:
            immediate_danger = st.checkbox("Immediate danger reported")
            ongoing_threat = st.checkbox("Ongoing threat reported")
        with col_safe2:
            safe_place = st.checkbox("Access to safe place confirmed")
            police_contacted = st.checkbox("Police already contacted")

        context_notes = st.text_area(
            "Additional context notes (e.g., language preference, communication needs)",
            height=80,
            max_chars=1000,
        )

    st.divider()

    # ── 5. Submission ─────────────────────────────────────────────────────────
    text_ok = char_count >= _MIN_CHARS
    submit_disabled = not consent or not text_ok

    col1, col2 = st.columns([1, 4])
    with col1:
        submit = st.button(
            "Submit & Screen",
            type="primary",
            disabled=submit_disabled,
            key="intake_submit",
        )

    if not consent and char_count > 0:
        st.warning("⚠️ Please provide consent before submitting.")
    elif consent and not text_ok and char_count > 0:
        st.warning(
            f"⚠️ Complaint text must be at least {_MIN_CHARS} characters "
            f"(currently {char_count})."
        )

    if submit:
        # Build StructuredContextInput
        structured_context = StructuredContextInput(
            social_identity_context=SocialIdentityContext(social_id),
            minority_community_context=MinorityCommunityContext(minority_id),
            incident_type=[IncidentType(it) for it in incident_types],
            immediate_danger=immediate_danger or None,
            ongoing_threat=ongoing_threat or None,
            safe_place_available=safe_place or None,
            police_contacted=police_contacted or None,
        )

        _handle_submission(
            consent=consent,
            complaint_text=complaint_text,
            audio_filename=audio_filename,
            context_notes=context_notes.strip() or None,
            structured_context=structured_context,
        )

    st.markdown("---")
    st.caption("**Phase 2 — Text Screening** · AI screening pipeline active.")


def _render_post_submission_receipt() -> None:
    """Show the case receipt and screening results after a successful submit."""
    case_id_str: str = st.session_state["last_case_id"]
    assessment = st.session_state["last_assessment"]

    st.divider()

    # Render neutral acknowledgement instead of AI screening result
    screening_results.render_complainant_acknowledgement(case_id_str)

    st.divider()

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Submit another case", key="intake_new"):
            for key in ["last_case_id", "last_assessment"]:
                if key in st.session_state:
                    del st.session_state[key]
            _reset_form()
            st.rerun()

    st.caption("**Phase 2 — Text Screening** · AI assists. Human decides.")


def _handle_submission(
    *,
    consent: bool,
    complaint_text: str,
    audio_filename: str | None,
    context_notes: str | None,
    structured_context: StructuredContextInput | None,
) -> None:
    """Validate inputs, persist the case, run screening, and update session state."""
    try:
        submission = CaseSubmission(
            consent_given=consent,
            complaint_text=complaint_text,
            audio_filename=audio_filename,
            context_notes=context_notes,
            structured_context=structured_context,
        )
    except ValidationError as exc:
        # Surface human-readable Pydantic errors; never echo raw complaint_text
        errors = "; ".join(e["msg"] for e in exc.errors())
        st.error(f"❌ Validation failed: {errors}")
        # Log only the error type, NOT the complaint content
        logger.warning("Intake validation error: %s", errors)
        return

    with st.spinner("Saving case…"):
        try:
            service = CaseService()
            result = service.submit_case(submission)
            case_id: uuid.UUID = result.case_id
        except Exception as exc:  # noqa: BLE001
            st.error(
                "❌ An error occurred while saving the case. "
                "Please try again or contact support."
            )
            logger.error(
                "Case submission failed: %s — %s",
                type(exc).__name__,
                str(exc),
            )
            return

    with st.spinner("Running AI screening via OpenAI…"):
        try:
            service = CaseService()
            assessment = service.run_screening(case_id)
        except Exception as exc:  # noqa: BLE001
            # Screening failure should NOT prevent the case from being recorded.
            # Store case_id but no assessment.
            st.warning(
                "⚠️ Case saved, but AI screening encountered an error. "
                "Human review is required."
            )
            logger.error(
                "Screening failed for case %s: %s — %s",
                case_id,
                type(exc).__name__,
                str(exc),
            )
            st.session_state["last_case_id"] = str(case_id)
            st.session_state["last_assessment"] = None
            _reset_form()
            st.rerun()
            return

    # Store in session state to show receipt; clear form fields
    st.session_state["last_case_id"] = str(case_id)
    st.session_state["last_assessment"] = assessment
    _reset_form()
    st.rerun()
