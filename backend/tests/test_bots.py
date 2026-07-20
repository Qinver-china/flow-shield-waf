"""Tests for bot management."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.bot_settings import RESERVED_CATEGORY_OTHER
from app.schemas.log import LogQuery
from app.services.bot_catalog import normalize_patterns, validate_category_value, validate_pattern
from app.services.logging.query_clickhouse import _where_clause


def test_normalize_patterns_dedupes_and_strips():
    patterns = normalize_patterns([" Googlebot ", "Googlebot", "Bingbot"])
    assert patterns == ["Googlebot", "Bingbot"]


def test_validate_pattern_rejects_invalid_regex():
    with pytest.raises(ValueError, match="无效的正则"):
        validate_pattern("/[/")


def test_validate_pattern_accepts_regex_form():
    validate_pattern("/googlebot/i")


def test_validate_category_value_rejects_other():
    with pytest.raises(ValueError, match="系统预留"):
        validate_category_value("other")


def test_where_clause_supports_bot_filters():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 2, 0, 0, 0)
    q = LogQuery(bot_name="Googlebot", bot_category="search_engine")
    where, params = _where_clause(q, start, end)
    assert "bot_name = {bot_name:String}" in where
    assert "bot_category = {bot_category:String}" in where
    assert params["bot_name"] == "Googlebot"
    assert params["bot_category"] == "search_engine"


@pytest.mark.asyncio
async def test_delete_bot_allows_former_builtin():
    from app.api.v1 import bots as bots_api

    row = MagicMock()
    row.is_builtin = True
    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.api.v1.bots.rule_sync.publish", new_callable=AsyncMock) as publish:
        result = await bots_api.delete_bot(1, db=db, _user=MagicMock())
    db.delete.assert_awaited_once_with(row)
    db.commit.assert_awaited()
    publish.assert_awaited()
    assert result["code"] == 0


@pytest.mark.asyncio
async def test_update_bot_allows_former_builtin_fields():
    from app.api.v1 import bots as bots_api
    from app.schemas.bot import BotProfileUpdate

    row = MagicMock()
    row.is_builtin = True
    row.ua_patterns = ["Old"]
    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    body = BotProfileUpdate(name="Renamed", ua_patterns=["NewBot"])
    with patch("app.api.v1.bots.rule_sync.publish", new_callable=AsyncMock):
        with patch("app.api.v1.bots.enrich_row", side_effect=lambda _row, data: data):
            with patch("app.api.v1.bots._out", return_value={"id": 1, "name": "Renamed"}):
                result = await bots_api.update_bot(1, body, db=db, _user=MagicMock())
    assert row.name == "Renamed"
    assert row.ua_patterns == ["NewBot"]
    assert result["code"] == 0


@pytest.mark.asyncio
async def test_build_config_includes_bots_without_action():
    from app.services import rule_sync

    bot = MagicMock()
    bot.id = 1
    bot.name = "Googlebot"
    bot.categories = ["search_engine"]
    bot.ua_patterns = ["Googlebot"]
    bot.enabled = True
    bot.verify_dns_suffix = ".googlebot.com"
    bot.site_ids = None

    category = MagicMock()
    category.value = "search_engine"

    class _Scalars:
        def __init__(self, items):
            self._items = items

        def all(self):
            return self._items

    class _Result:
        def __init__(self, items=None):
            self._items = items or []

        def scalars(self):
            return _Scalars(self._items)

    empty = _Result()
    bot_result = _Result([bot])
    category_result = _Result([category])
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[empty, empty, empty, empty, empty, empty, bot_result, category_result]
    )

    with patch("app.services.rule_sync.waf_settings.get_runtime_settings", new_callable=AsyncMock) as mock_settings:
        mock_settings.return_value = {
            "logging": {},
            "block_page": {},
            "captcha_footer": {},
        }
        cfg = await rule_sync.build_config(db)

    assert len(cfg["bots"]) == 1
    assert cfg["bots"][0]["name"] == "Googlebot"
    assert cfg["bots"][0]["categories"] == ["search_engine"]
    assert "action" not in cfg["bots"][0]
    assert "bot" not in cfg["settings"]
    assert cfg["bot_category_values"] == ["search_engine"]
    assert "patterns" in cfg["crawler_detect"]
    assert "exclusions" in cfg["crawler_detect"]


def test_reserved_category_other_constant():
    assert RESERVED_CATEGORY_OTHER == "other"


def test_apply_category_filter_supports_multiple():
    from sqlalchemy import select

    from app.api.v1.bots import _apply_category_filter
    from app.models import BotProfile

    stmt = select(BotProfile)
    filtered = _apply_category_filter(stmt, ["search_engine", "ai_crawler"])
    compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert "bot_profiles.categories" in compiled or "categories" in compiled
    assert "search_engine" in compiled
    assert "ai_crawler" in compiled
