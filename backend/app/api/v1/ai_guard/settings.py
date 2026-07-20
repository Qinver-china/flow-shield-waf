from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.schemas.ai_guard import AiGuardSettingOut, AiGuardSettingUpdate
from app.schemas.common import ok
from app.services.ai_guard.config import get_or_create_setting, load_runtime_config
from app.services.ai_guard.crypto import PASSWORD_MASK, encrypt_secret
from app.services.ai_guard.llm.client import LlmClient
from app.services.ai_guard.llm.errors import format_llm_error

router = APIRouter()


def _out(row) -> dict:
    return AiGuardSettingOut(
        enabled=row.enabled,
        provider_base_url=row.provider_base_url,
        api_key_set=bool(row.api_key_encrypted),
        model=row.model,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        chat_enabled=row.chat_enabled,
        floating_chat_enabled=bool(getattr(row, "floating_chat_enabled", True)),
        defense_enabled=row.defense_enabled,
        default_apply_mode=row.default_apply_mode,
        max_logs_per_analysis=row.max_logs_per_analysis,
        analysis_cooldown_sec=row.analysis_cooldown_sec,
        auto_block_min_confidence=row.auto_block_min_confidence,
    ).model_dump()


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await get_or_create_setting(db)
    return ok(_out(row))


@router.put("")
async def update_settings(
    body: AiGuardSettingUpdate,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    row = await get_or_create_setting(db)
    data = body.model_dump(exclude_unset=True)
    api_key = data.pop("api_key", None)
    if api_key is not None and api_key not in ("", PASSWORD_MASK):
        row.api_key_encrypted = encrypt_secret(api_key.strip())
    if "provider_base_url" in data and isinstance(data["provider_base_url"], str):
        data["provider_base_url"] = data["provider_base_url"].strip().rstrip("/")
    if "model" in data and isinstance(data["model"], str):
        data["model"] = data["model"].strip()
    for k, v in data.items():
        setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return ok(_out(row))


@router.get("/models")
async def list_provider_models(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cfg = await load_runtime_config(db)
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")
    try:
        client = LlmClient(cfg)
        models = await client.list_model_ids()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=format_llm_error(exc)) from exc
    return ok({"models": models})


@router.post("/test")
async def test_connection(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cfg = await load_runtime_config(db)
    if not cfg.api_key:
        raise HTTPException(status_code=400, detail="请先配置 API Key")
    try:
        client = LlmClient(cfg)
        reply = await client.test_connection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=format_llm_error(exc)) from exc
    return ok({"reply": reply})
