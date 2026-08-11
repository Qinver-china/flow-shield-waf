"""Auth endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import auth as auth_api


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
