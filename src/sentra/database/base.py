"""
Declarative base for all SENTRA SQLAlchemy ORM models.

Import ``Base`` from this module when defining new mapped classes.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all SENTRA ORM models."""
