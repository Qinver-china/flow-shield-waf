"""Tests for bot category management."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.constants.bot_settings import RESERVED_CATEGORY_OTHER
from app.schemas.bot_category import BotCategoryCreate
from app.services.bot_catalog import validate_category_value


def test_validate_category_value_accepts_custom_slug():
    assert validate_category_value("seo_tool") == "seo_tool"


def test_validate_category_value_rejects_other():
    with pytest.raises(ValueError, match="系统预留"):
        validate_category_value(RESERVED_CATEGORY_OTHER)


def test_create_schema_rejects_other():
    with pytest.raises(ValidationError):
        BotCategoryCreate(value=RESERVED_CATEGORY_OTHER, label="其他")


@pytest.mark.asyncio
async def test_delete_other_category_rejected():
    from app.api.v1 import bot_categories as api

    row = MagicMock()
    row.is_builtin = True
    row.value = RESERVED_CATEGORY_OTHER
    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    with pytest.raises(HTTPException) as exc:
        await api.delete_bot_category(1, db=db, _user=MagicMock())
    assert exc.value.status_code == 400
    assert "other" in str(exc.value.detail)


@pytest.mark.asyncio
async def test_delete_former_builtin_category_allowed_when_unreferenced():
    from unittest.mock import patch

    from app.api.v1 import bot_categories as api

    row = MagicMock()
    row.is_builtin = True
    row.value = "search_engine"
    db = AsyncMock()
    db.get = AsyncMock(return_value=row)
    db.delete = AsyncMock()
    db.commit = AsyncMock()
    with patch(
        "app.api.v1.bot_categories.find_bot_category_references",
        new_callable=AsyncMock,
    ) as refs:
        with patch("app.api.v1.bot_categories.rule_sync.publish", new_callable=AsyncMock) as publish:
            refs.return_value = []
            result = await api.delete_bot_category(1, db=db, _user=MagicMock())
    db.delete.assert_awaited_once_with(row)
    publish.assert_awaited()
    assert result["code"] == 0
