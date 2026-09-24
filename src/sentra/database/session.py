"""
SQLAlchemy engine, session factory, and base setup for SENTRA.

Usage
-----
Import ``SessionLocal`` wherever a database session is needed:

    from sentra.database.session import SessionLocal

    with SessionLocal() as session:
        ...

The engine is created lazily on first access and is shared application-wide.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from sentra.config.settings import get_settings

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _create_engine():  # noqa: ANN202
    settings = get_settings()
    if settings.is_sqlite:
        # SQLite: single-file, thread-safe mode, no pool sizing.
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=settings.is_development,
        )
    # PostgreSQL (and other drivers)
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,       # detect stale connections
        pool_size=5,
        max_overflow=10,
        echo=settings.is_development,  # log SQL in dev only
    )


# Lazy engine — created on first import of this module.
engine = _create_engine()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Context manager helper
# ---------------------------------------------------------------------------


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session.

    Commits on successful exit, rolls back on exception.

    Example::

        with get_session() as session:
            session.add(record)
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def check_database_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
