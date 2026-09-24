"""
Typed application settings for SENTRA.

Settings are loaded from environment variables (and an optional .env file).
Use ``get_settings()`` to obtain the singleton instance throughout the app.

Never hardcode secrets. Refer to .env.example for all required variables.
"""

from __future__ import annotations

import functools
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide typed configuration.

    All values are read from environment variables. An optional ``.env``
    file in the project root is loaded automatically when it exists.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────────────────────
    sentra_env: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Python logging level.",
    )
    secret_key: SecretStr = Field(
        default=SecretStr("insecure-dev-key-replace-in-production"),
        description="Secret key for session signing. Must be overridden in production.",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        # SQLite is used as a zero-config local fallback when DATABASE_URL is
        # not set. Set DATABASE_URL in .env to switch to PostgreSQL.
        default="sqlite:///./sentra_dev.db",
        description=(
            "SQLAlchemy connection string. "
            "Defaults to a local SQLite file for development. "
            "Set DATABASE_URL=postgresql+psycopg2://... in .env for PostgreSQL."
        ),
    )

    @property
    def db_driver(self) -> str:
        """Return the database driver name (e.g. 'sqlite', 'postgresql')."""
        return self.database_url.split("+")[0].split(":")[0]

    @property
    def is_sqlite(self) -> bool:
        """Return True when using the local SQLite fallback."""
        return self.db_driver == "sqlite"

    # ── Application limits ───────────────────────────────────────────────────
    max_text_chars: int = Field(
        default=5000,
        description="Maximum characters allowed in a complaint text submission.",
        ge=1,
    )
    max_audio_mb: int = Field(
        default=50,
        description="Maximum audio file size in megabytes.",
        ge=1,
    )

    @property
    def is_development(self) -> bool:
        """Return True when running in development mode."""
        return self.sentra_env == "development"

    @property
    def is_production(self) -> bool:
        """Return True when running in production mode."""
        return self.sentra_env == "production"

    # ── OpenAI (Phase 2 — LLM Text Screening) ────────────────────────────────
    #
    # Required for Phase 2 LLM-powered text screening.
    # Set OPENAI_API_KEY and OPENAI_MODEL in .env (never in source code).
    # See .env.example for documentation.

    openai_api_key: SecretStr | None = Field(
        default=None,
        description=(
            "OpenAI API key. Required for Phase 2 LLM text screening. "
            "Set OPENAI_API_KEY in .env. Never hardcode. Never log."
        ),
    )
    openai_model: str = Field(
        default="gpt-4o",
        description=(
            "OpenAI model identifier for text screening. "
            "The application validates model availability before the first screening call. "
            "If unavailable, screening fails safely to INSUFFICIENT_DATA. "
            "Override with OPENAI_MODEL in .env."
        ),
    )
    openai_timeout_seconds: int = Field(
        default=30,
        description="OpenAI API request timeout in seconds.",
        ge=5,
        le=120,
    )
    openai_max_retries: int = Field(
        default=2,
        description="Maximum retries on transient OpenAI API errors (not auth/model errors).",
        ge=0,
        le=5,
    )

    @property
    def openai_enabled(self) -> bool:
        """Return True when an OpenAI API key is configured."""
        return self.openai_api_key is not None


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    The first call reads from environment / .env file.
    Subsequent calls return the cached instance.
    """
    return Settings()
