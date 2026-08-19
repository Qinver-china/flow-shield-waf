"""Engine upload limit and body-inspect flag helpers."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.constants.engine_settings import (
    DEFAULT_MAX_UPLOAD_SIZE_MB,
    DEFAULT_ORIGIN_READ_TIMEOUT_SEC,
)
from app.schemas.waf_setting import EngineSettings
from app.services.engine_inspect import inspect_flags_from_items
from app.services.nginx_conf import (
    apply_client_max_body_size,
    apply_origin_read_timeout,
    render_client_max_body_size,
    render_origin_read_timeout,
)


def test_engine_settings_default_and_bounds():
    assert EngineSettings().max_upload_size_mb == DEFAULT_MAX_UPLOAD_SIZE_MB
    assert EngineSettings().origin_read_timeout_sec == DEFAULT_ORIGIN_READ_TIMEOUT_SEC
    EngineSettings(max_upload_size_mb=1, origin_read_timeout_sec=5)
    EngineSettings(max_upload_size_mb=2048, origin_read_timeout_sec=600)
    for bad in (0, 2049, -1):
        try:
            EngineSettings(max_upload_size_mb=bad)
            assert False, f"expected validation error for {bad}"
        except ValidationError:
            pass
    for bad in (4, 601, 0):
        try:
            EngineSettings(origin_read_timeout_sec=bad)
            assert False, f"expected validation error for timeout {bad}"
        except ValidationError:
            pass


def test_render_client_max_body_size():
    assert render_client_max_body_size(50) == "client_max_body_size 50m;\n"
    assert render_client_max_body_size(256) == "client_max_body_size 256m;\n"


def test_apply_client_max_body_size(tmp_path: Path, monkeypatch):
    target = tmp_path / "snippets" / "client-max-body.conf"
    monkeypatch.setattr(
        "app.services.nginx_conf.settings.engine_client_max_body_conf",
        str(target),
    )
    apply_client_max_body_size(128)
    assert target.read_text(encoding="utf-8") == "client_max_body_size 128m;\n"


def test_render_origin_read_timeout():
    assert render_origin_read_timeout(60) == (
        "proxy_read_timeout 60s;\nproxy_send_timeout 60s;\n"
    )
    assert render_origin_read_timeout(120) == (
        "proxy_read_timeout 120s;\nproxy_send_timeout 120s;\n"
    )


def test_apply_origin_read_timeout(tmp_path: Path, monkeypatch):
    target = tmp_path / "snippets" / "origin-timeout.conf"
    monkeypatch.setattr(
        "app.services.nginx_conf.settings.engine_origin_timeout_conf",
        str(target),
    )
    apply_origin_read_timeout(180)
    assert target.read_text(encoding="utf-8") == (
        "proxy_read_timeout 180s;\nproxy_send_timeout 180s;\n"
    )


def test_inspect_flags_skip_when_unused():
    flags = inspect_flags_from_items(
        [
            {
                "enabled": True,
                "conditions": {
                    "logic": "and",
                    "conditions": [{"field": "http.method", "op": "eq", "value": "GET"}],
                },
            }
        ]
    )
    assert flags == {"body": False, "upload": False}


def test_inspect_flags_detect_upload_and_ignore_disabled():
    flags = inspect_flags_from_items(
        [
            {
                "enabled": False,
                "conditions": {
                    "conditions": [{"field": "http.upload.ext", "op": "in_list", "value": ["php"]}]
                },
            },
            {
                "enabled": True,
                "conditions": {
                    "conditions": [
                        {"field": "http.upload.filename", "op": "contains", "value": ".php"}
                    ]
                },
            },
        ]
    )
    assert flags["upload"] is True
    assert flags["body"] is False


def test_inspect_flags_detect_body_raw():
    flags = inspect_flags_from_items(
        [
            {
                "enabled": True,
                "conditions": {
                    "conditions": [{"field": "http.body.raw", "op": "regex", "value": "union"}]
                },
            }
        ]
    )
    assert flags["body"] is True
    assert flags["upload"] is False


def test_inspect_flags_from_ratelimit_keys():
    flags = inspect_flags_from_items(
        [
            {
                "enabled": True,
                "keys": [{"field": "http.body.form", "arg": "user"}],
                "conditions": None,
            }
        ]
    )
    assert flags["body"] is True
    assert flags["upload"] is False


@pytest.mark.asyncio
async def test_regenerate_snippet_write_failure_skips_reload(tmp_path, monkeypatch):
    from app.services import nginx_conf
    from app.services.nginx_conf import EngineReloadResult

    row = MagicMock()
    row.max_upload_size_mb = 50
    row.origin_read_timeout_sec = 60

    async def fake_get_or_create(_db):
        return row

    def fail_write(_mb):
        raise OSError("disk full")

    reload_called = False

    async def fake_reload():
        nonlocal reload_called
        reload_called = True
        return EngineReloadResult(ok=True)

    class _Scalars:
        def all(self):
            return []

    class _Result:
        def scalars(self):
            return _Scalars()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())

    monkeypatch.setattr(
        "app.services.waf_settings.get_or_create", fake_get_or_create
    )
    monkeypatch.setattr(nginx_conf, "apply_client_max_body_size", fail_write)
    monkeypatch.setattr(nginx_conf, "trigger_reload", fake_reload)
    monkeypatch.setattr(nginx_conf.settings, "engine_conf_dir", str(tmp_path))

    result = await nginx_conf.regenerate(db)
    assert result.ok is False
    assert result.reason == "engine"
    assert "disk full" in (result.detail or "")
    assert reload_called is False


def _empty_site_db():
    class _Scalars:
        def all(self):
            return []

    class _Result:
        def scalars(self):
            return _Scalars()

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_Result())
    return db


@pytest.mark.asyncio
async def test_regenerate_skips_reload_when_engine_down(tmp_path, monkeypatch):
    from app.services import nginx_conf
    from app.services.nginx_conf import EngineReloadResult

    row = MagicMock()
    row.max_upload_size_mb = 50
    row.origin_read_timeout_sec = 60

    reload_called = False

    async def fake_reload():
        nonlocal reload_called
        reload_called = True
        return EngineReloadResult(ok=True)

    monkeypatch.setattr(
        "app.services.waf_settings.get_or_create", AsyncMock(return_value=row)
    )
    monkeypatch.setattr(nginx_conf, "apply_client_max_body_size", lambda _mb: None)
    monkeypatch.setattr(nginx_conf, "apply_origin_read_timeout", lambda _sec: None)
    monkeypatch.setattr(nginx_conf, "trigger_reload", fake_reload)
    monkeypatch.setattr(nginx_conf, "_engine_is_running", lambda: False)
    monkeypatch.setattr(nginx_conf.settings, "engine_conf_dir", str(tmp_path))

    result = await nginx_conf.regenerate(
        _empty_site_db(), skip_reload_if_engine_down=True
    )
    assert result.ok is True
    assert reload_called is False


@pytest.mark.asyncio
async def test_regenerate_reloads_when_engine_up_even_if_skip_flag(tmp_path, monkeypatch):
    from app.services import nginx_conf
    from app.services.nginx_conf import EngineReloadResult

    row = MagicMock()
    row.max_upload_size_mb = 50
    row.origin_read_timeout_sec = 60

    reload_called = False

    async def fake_reload():
        nonlocal reload_called
        reload_called = True
        return EngineReloadResult(ok=True)

    monkeypatch.setattr(
        "app.services.waf_settings.get_or_create", AsyncMock(return_value=row)
    )
    monkeypatch.setattr(nginx_conf, "apply_client_max_body_size", lambda _mb: None)
    monkeypatch.setattr(nginx_conf, "apply_origin_read_timeout", lambda _sec: None)
    monkeypatch.setattr(nginx_conf, "trigger_reload", fake_reload)
    monkeypatch.setattr(nginx_conf, "_engine_is_running", lambda: True)
    monkeypatch.setattr(nginx_conf.settings, "engine_conf_dir", str(tmp_path))

    result = await nginx_conf.regenerate(
        _empty_site_db(), skip_reload_if_engine_down=True
    )
    assert result.ok is True
    assert reload_called is True


@pytest.mark.asyncio
async def test_regenerate_default_still_reloads_when_engine_down(tmp_path, monkeypatch):
    from app.services import nginx_conf
    from app.services.nginx_conf import EngineReloadResult

    row = MagicMock()
    row.max_upload_size_mb = 50
    row.origin_read_timeout_sec = 60

    reload_called = False

    async def fake_reload():
        nonlocal reload_called
        reload_called = True
        return EngineReloadResult(ok=True)

    monkeypatch.setattr(
        "app.services.waf_settings.get_or_create", AsyncMock(return_value=row)
    )
    monkeypatch.setattr(nginx_conf, "apply_client_max_body_size", lambda _mb: None)
    monkeypatch.setattr(nginx_conf, "apply_origin_read_timeout", lambda _sec: None)
    monkeypatch.setattr(nginx_conf, "trigger_reload", fake_reload)
    monkeypatch.setattr(nginx_conf, "_engine_is_running", lambda: False)
    monkeypatch.setattr(nginx_conf.settings, "engine_conf_dir", str(tmp_path))

    result = await nginx_conf.regenerate(_empty_site_db())
    assert result.ok is True
    assert reload_called is True
