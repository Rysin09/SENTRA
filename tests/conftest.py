"""
Shared pytest fixtures for SENTRA tests.

Fixtures here are available to all tests without explicit imports.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import sentra.database.models  # noqa: F401 — registers ORM classes on Base
from sentra.database.base import Base
from sentra.domain.models import CaseInput
from sentra.domain.schemas import CaseSubmission

# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_case_input() -> CaseInput:
    """Minimal valid CaseInput for use in tests."""
    return CaseInput(
        complaint_text="Test complaint text for unit testing.",
        consent_given=True,
    )


@pytest.fixture
def long_case_input() -> CaseInput:
    """CaseInput with a longer complaint text."""
    return CaseInput(
        complaint_text="A" * 4000,
        consent_given=True,
        context_notes="Integration test context.",
    )


@pytest.fixture
def valid_submission() -> CaseSubmission:
    """A minimal valid CaseSubmission."""
    return CaseSubmission(
        complaint_text="This is a test complaint with enough characters.",
        consent_given=True,
    )


@pytest.fixture
def submission_with_audio() -> CaseSubmission:
    """A valid CaseSubmission with an audio filename."""
    return CaseSubmission(
        complaint_text="Test complaint including audio reference.",
        consent_given=True,
        audio_filename="recording.wav",
        context_notes="Language: English",
    )


# ---------------------------------------------------------------------------
# In-memory SQLite database fixtures for integration tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def in_memory_engine():
    """SQLite in-memory engine for the entire test session.

    Uses ``check_same_thread=False`` so pytest can share it across threads.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(in_memory_engine) -> Session:  # noqa: ANN001
    """A clean, rolled-back SQLAlchemy session per test.

    Each test gets an isolated transaction that is rolled back after
    the test completes, keeping the database clean for the next test.
    """
    connection = in_memory_engine.connect()
    transaction = connection.begin()
    SessionFactory = sessionmaker(bind=connection, expire_on_commit=False)  # noqa: N806
    session = SessionFactory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
