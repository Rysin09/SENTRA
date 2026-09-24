"""
Unit tests for the Settings configuration.

Tests verify that defaults are sane and that invalid values are rejected.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentra.config.settings import Settings, get_settings


@pytest.mark.unit
class TestSettingsDefaults:
    """Settings default values are safe and sane."""

    def test_default_env_is_development(self) -> None:
        s = Settings()
        assert s.sentra_env == "development"

    def test_default_log_level_is_info(self) -> None:
        s = Settings()
        assert s.log_level == "INFO"

    def test_is_development_property(self) -> None:
        s = Settings()
        assert s.is_development is True
        assert s.is_production is False

    def test_max_text_chars_positive(self) -> None:
        s = Settings()
        assert s.max_text_chars > 0

    def test_max_audio_mb_positive(self) -> None:
        s = Settings()
        assert s.max_audio_mb > 0


@pytest.mark.unit
class TestSettingsValidation:
    """Invalid settings values are rejected at construction time."""

    def test_invalid_env_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(sentra_env="invalid_env")  # type: ignore[arg-type]

    def test_invalid_log_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            Settings(log_level="TRACE")  # type: ignore[arg-type]

    def test_max_text_chars_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            Settings(max_text_chars=0)


@pytest.mark.unit
def test_get_settings_returns_same_instance() -> None:
    """get_settings() must return a cached singleton."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
