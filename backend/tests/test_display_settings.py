"""Tests for display/timezone settings."""

from types import SimpleNamespace

from app.constants.display_settings import ALLOWED_TIMEZONES, DEFAULT_TIMEZONE
from app.schemas.waf_setting import DisplaySettings, DisplaySettingsOut
from app.services.waf_settings import infer_panel_public_url


def _make_request(
    *,
    scheme: str = "http",
    host: str | None = "127.0.0.1:9000",
    forwarded_host: str | None = None,
    forwarded_proto: str | None = None,
    forwarded_port: str | None = None,
    base_url: str = "http://127.0.0.1/",
):
    headers = {}
    if host is not None:
        headers["host"] = host
    if forwarded_host is not None:
        headers["x-forwarded-host"] = forwarded_host
    if forwarded_proto is not None:
        headers["x-forwarded-proto"] = forwarded_proto
    if forwarded_port is not None:
        headers["x-forwarded-port"] = forwarded_port
    return SimpleNamespace(
        url=SimpleNamespace(scheme=scheme),
        headers=headers,
        base_url=base_url,
    )


def test_display_settings_default_timezone():
    settings = DisplaySettings(panel_public_url="http://127.0.0.1:9000")
    assert settings.timezone == DEFAULT_TIMEZONE
    assert settings.panel_public_url == "http://127.0.0.1:9000"


def test_display_settings_strips_trailing_slash_from_panel_url():
    settings = DisplaySettings(panel_public_url="https://waf.example.com:9000/")
    assert settings.panel_public_url == "https://waf.example.com:9000"


def test_display_settings_rejects_unknown_timezone():
    try:
        DisplaySettings(timezone="Invalid/Zone", panel_public_url="http://127.0.0.1:9000")
        assert False, "expected validation error"
    except ValueError:
        pass


def test_allowed_timezones_include_shanghai():
    assert "Asia/Shanghai" in ALLOWED_TIMEZONES


def test_infer_panel_public_url_from_host_with_port():
    request = _make_request(host="127.0.0.1:9000")
    assert infer_panel_public_url(request) == "http://127.0.0.1:9000"


def test_infer_panel_public_url_appends_forwarded_port():
    request = _make_request(
        host="127.0.0.1",
        forwarded_port="9000",
    )
    assert infer_panel_public_url(request) == "http://127.0.0.1:9000"


def test_infer_panel_public_url_forwarded_host_with_port_header():
    request = _make_request(
        host="127.0.0.1",
        forwarded_host="waf.example.com",
        forwarded_proto="https",
        forwarded_port="9443",
    )
    assert infer_panel_public_url(request) == "https://waf.example.com:9443"


def test_infer_panel_public_url_omits_default_http_port():
    request = _make_request(host="waf.example.com", forwarded_port="80")
    assert infer_panel_public_url(request) == "http://waf.example.com"


def test_display_settings_out_exposes_runtime_ports():
    row = SimpleNamespace(
        timezone="Asia/Shanghai",
        panel_public_url="https://waf.example.com:9010",
        acme_account_email="ops@example.com",
    )
    out = DisplaySettingsOut.from_row(row, backend_port=8001)
    assert out.backend_port == 8001
    assert out.panel_port == 9010
    assert out.acme_account_email == "ops@example.com"


def test_display_settings_normalizes_acme_email():
    settings = DisplaySettings(
        panel_public_url="http://127.0.0.1:9000",
        acme_account_email="  Ops@Example.COM  ",
    )
    assert settings.acme_account_email == "ops@example.com"


def test_display_settings_allows_empty_acme_email():
    settings = DisplaySettings(
        panel_public_url="http://127.0.0.1:9000",
        acme_account_email="  ",
    )
    assert settings.acme_account_email is None
