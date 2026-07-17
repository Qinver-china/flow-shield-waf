"""Auth endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import auth as auth_api
from app.core.config import Settings


def test_validate_production_secrets_rejects_defaults():
    settings = Settings(
        jwt_secret="change_me",
        waf_challenge_secret="change_me_challenge",
        waf_admin_password="admin888",
        waf_allow_insecure_defaults=False,
    )
    with pytest.raises(SystemExit):
        settings.validate_production_secrets()


def test_validate_production_secrets_allows_dev_override():
    settings = Settings(
        jwt_secret="change_me",
        waf_challenge_secret="change_me_challenge",
        waf_admin_password="admin888",
        waf_allow_insecure_defaults=True,
    )
    settings.validate_production_secrets()


@pytest.mark.asyncio
async def test_refresh_rejects_inactive_user():
    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=MagicMock(is_active=False))
        )
    )
    with (
        patch("app.api.v1.auth.decode_token", return_value={"type": "refresh", "sub": "admin"}),
        pytest.raises(HTTPException) as exc,
    ):
        await auth_api.refresh(MagicMock(refresh_token="token"), db=db)
    assert exc.value.status_code == 401
