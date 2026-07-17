"""Shared FastAPI dependencies: auth + pagination."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import decode_token
from app.models import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="未认证或登录已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if cred is None:
        raise unauthorized
    try:
        payload = decode_token(cred.credentials)
    except Exception as exc:  # noqa: BLE001
        raise unauthorized from exc
    if payload.get("type") != "access":
        raise unauthorized

    username = payload.get("sub")
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized
    return user


class Pagination:
    def __init__(self, page: int = 1, page_size: int = 20):
        self.page = max(1, page)
        self.page_size = min(200, max(1, page_size))

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
