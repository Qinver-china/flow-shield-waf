from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.rate_limit import check_login_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ChangeUsernameRequest,
    InitialSetupRequest,
    LoginRequest,
    RefreshRequest,
)
from app.schemas.common import ok

router = APIRouter()


async def _admin_exists(db: AsyncSession) -> bool:
    count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    return int(count or 0) > 0


def _token_payload(username: str) -> dict:
    return {
        "access_token": create_access_token(username),
        "refresh_token": create_refresh_token(username),
        "token_type": "Bearer",
    }


@router.get("/setup-status")
async def setup_status(db: AsyncSession = Depends(get_db)):
    return ok({"needs_setup": not await _admin_exists(db)})


@router.post("/initial-setup")
async def initial_setup(
    body: InitialSetupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_login_rate_limit(request)
    if await _admin_exists(db):
        raise HTTPException(status_code=400, detail="管理员账号已存在")
    db.add(User(
        username=body.new_username,
        password_hash=hash_password(body.new_password),
        is_active=True,
    ))
    await db.commit()
    return ok(_token_payload(body.new_username))


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_login_rate_limit(request)
    user = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    return ok(_token_payload(user.username))


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="refresh token 无效") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="refresh token 无效")
    username = payload.get("sub")
    user = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="refresh token 无效")
    return ok(_token_payload(user.username))


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return ok({"id": user.id, "username": user.username, "is_active": user.is_active})


@router.put("/username")
async def change_username(
    body: ChangeUsernameRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if body.new_username == user.username:
        raise HTTPException(status_code=400, detail="新用户名与当前相同")
    exists = (
        await db.execute(select(User).where(User.username == body.new_username))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="该用户名已被占用")
    user.username = body.new_username
    await db.commit()
    await db.refresh(user)
    return ok({
        "username": user.username,
        **_token_payload(user.username),
    })


@router.put("/password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与当前密码相同")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return ok()
