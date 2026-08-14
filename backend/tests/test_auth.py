"""Auth endpoint tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1 import auth as auth_api
from app.schemas.auth import normalize_admin_username


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


def test_normalize_admin_username_strips_and_accepts():
    assert normalize_admin_username("  owner_1  ") == "owner_1"


def test_normalize_admin_username_rejects_invalid():
    with pytest.raises(ValueError):
        normalize_admin_username("bad name")


@pytest.mark.asyncio
async def test_setup_status_true_when_no_admin():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=0)))
    result = await auth_api.setup_status(db=db)
    assert result["data"]["needs_setup"] is True


@pytest.mark.asyncio
async def test_setup_status_false_when_admin_exists():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=1)))
    result = await auth_api.setup_status(db=db)
    assert result["data"]["needs_setup"] is False


@pytest.mark.asyncio
async def test_initial_setup_rejected_when_admin_exists():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=1)))
    with (
        patch("app.api.v1.auth.check_login_rate_limit", new_callable=AsyncMock),
        pytest.raises(HTTPException) as exc,
    ):
        await auth_api.initial_setup(
            MagicMock(new_username="owner", new_password="secret12"),
            request=MagicMock(),
            db=db,
        )
    assert exc.value.status_code == 400
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_initial_setup_creates_admin_when_empty():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(scalar_one=MagicMock(return_value=0)))
    db.add = MagicMock()
    db.commit = AsyncMock()
    with (
        patch("app.api.v1.auth.check_login_rate_limit", new_callable=AsyncMock),
        patch("app.api.v1.auth.hash_password", return_value="newhash"),
        patch("app.api.v1.auth.create_access_token", return_value="access"),
        patch("app.api.v1.auth.create_refresh_token", return_value="refresh"),
    ):
        result = await auth_api.initial_setup(
            MagicMock(new_username="owner", new_password="secret12"),
            request=MagicMock(),
            db=db,
        )
    db.add.assert_called_once()
    created = db.add.call_args[0][0]
    assert created.username == "owner"
    assert created.password_hash == "newhash"
    db.commit.assert_awaited()
    assert result["data"]["access_token"] == "access"
    assert result["data"]["refresh_token"] == "refresh"
