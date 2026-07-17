"""Tests for display/timezone settings."""

from app.constants.display_settings import ALLOWED_TIMEZONES, DEFAULT_TIMEZONE
from app.schemas.waf_setting import DisplaySettings


def test_display_settings_default_timezone():
    settings = DisplaySettings()
    assert settings.timezone == DEFAULT_TIMEZONE


def test_display_settings_rejects_unknown_timezone():
    try:
        DisplaySettings(timezone="Invalid/Zone")
        assert False, "expected validation error"
    except ValueError:
        pass


def test_allowed_timezones_include_shanghai():
    assert "Asia/Shanghai" in ALLOWED_TIMEZONES
