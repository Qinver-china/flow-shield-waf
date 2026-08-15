"""Tests for slide captcha service."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.internal.slide_captcha import _ensure_local
from app.services.slide_captcha.service import SlideCaptchaService


def test_ensure_local_allows_unix_socket_peer():
    _ensure_local(SimpleNamespace(client=None))
    _ensure_local(SimpleNamespace(client=SimpleNamespace(host="")))


def test_ensure_local_allows_loopback():
    _ensure_local(SimpleNamespace(client=SimpleNamespace(host="127.0.0.1")))
    _ensure_local(SimpleNamespace(client=SimpleNamespace(host="::1")))


def test_ensure_local_rejects_remote_tcp():
    with pytest.raises(HTTPException) as exc:
        _ensure_local(SimpleNamespace(client=SimpleNamespace(host="8.8.8.8")))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_slide_captcha_issue_and_verify(monkeypatch):
    from app.core import redis as redis_mod
    from app.core.config import settings

    assets = Path(__file__).resolve().parents[2] / "slide_captcha"
    monkeypatch.setattr(settings, "slide_captcha_assets_dir", str(assets.resolve()))

    store: dict[str, str] = {}

    class FakeRedis:
        async def set(self, key: str, value: str, ex: int | None = None):  # noqa: ARG002
            store[key] = value

        async def get(self, key: str):
            return store.get(key)

        async def delete(self, key: str):
            store.pop(key, None)

    monkeypatch.setattr(redis_mod, "get_redis", lambda: FakeRedis())

    issued = await SlideCaptchaService.issue()
    assert issued["captcha_key"]
    assert issued["image_base64"].startswith("data:image/jpeg;base64,")
    assert issued["tile_base64"].startswith("data:image/png;base64,")

    key = issued["captcha_key"]
    raw = store[f"waf:slide_cap:{key}"]
    target = json.loads(raw)
    ok = await SlideCaptchaService.verify(key, int(target["dx"]), int(target["dy"]))
    assert ok is True
    assert f"waf:slide_cap:{key}" not in store

    bad = await SlideCaptchaService.verify(key, 0, 0)
    assert bad is False
