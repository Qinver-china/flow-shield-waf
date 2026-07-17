"""Tests for log retention settings."""
import pytest

from app.constants.logging_settings import DEFAULT_LOG_RETENTION_DAYS
from app.schemas.logging_settings import LoggingSettings
from app.services.logging.retention_ttl import clamp_retention_days


def test_default_log_retention_days():
    assert DEFAULT_LOG_RETENTION_DAYS == 30


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (1, 1),
        (30, 30),
        (365, 365),
        (0, 1),
        (999, 365),
    ],
)
def test_clamp_retention_days(raw, expected):
    assert clamp_retention_days(raw) == expected


def test_logging_settings_schema_includes_retention():
    settings = LoggingSettings()
    assert settings.log_retention_days == DEFAULT_LOG_RETENTION_DAYS
