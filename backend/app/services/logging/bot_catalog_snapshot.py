"""In-memory snapshot of bot profiles from Redis waf:config (worker ingest)."""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("waf.bot_catalog_snapshot")

CONFIG_KEY = "waf:config"
VERSION_KEY = "waf:config:version"

_bots: list[dict[str, Any]] = []
_category_values: set[str] = set()
_version: int = -1


def get_bots() -> list[dict[str, Any]]:
    return _bots


def get_category_values() -> set[str]:
    return _category_values


def get_cached_version() -> int:
    return _version


async def refresh_from_redis(redis) -> None:
    """Reload bot list when waf:config:version changes."""
    global _bots, _category_values, _version
    try:
        raw_ver = await redis.get(VERSION_KEY)
        ver = int(raw_ver) if raw_ver is not None else -1
    except (TypeError, ValueError):
        ver = -1

    if ver == _version and _bots:
        return

    try:
        raw_cfg = await redis.get(CONFIG_KEY)
        if not raw_cfg:
            _bots = []
            _category_values = set()
            _version = ver
            return
        cfg = json.loads(raw_cfg)
        bots = cfg.get("bots")
        _bots = bots if isinstance(bots, list) else []
        raw_cats = cfg.get("bot_category_values")
        if isinstance(raw_cats, list):
            _category_values = {str(v) for v in raw_cats if v}
        else:
            _category_values = set()
        _version = ver
        log.debug(
            "bot catalog snapshot refreshed: version=%s bots=%d categories=%d",
            ver,
            len(_bots),
            len(_category_values),
        )
    except Exception:  # noqa: BLE001
        log.exception("bot catalog snapshot refresh failed")
