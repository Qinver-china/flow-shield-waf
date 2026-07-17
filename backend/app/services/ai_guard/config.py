"""Load AI Guard runtime configuration."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardSetting
from app.services.ai_guard.crypto import decrypt_secret

SETTING_ID = 1


@dataclass(frozen=True)
class AiGuardRuntimeConfig:
    enabled: bool
    provider_base_url: str
    api_key: str | None
    model: str
    temperature: float
    max_tokens: int
    chat_enabled: bool
    defense_enabled: bool
    default_apply_mode: str
    max_logs_per_analysis: int
    analysis_cooldown_sec: int
    auto_block_min_confidence: float


async def get_or_create_setting(db: AsyncSession) -> AiGuardSetting:
    row = await db.get(AiGuardSetting, SETTING_ID)
    if row is None:
        row = AiGuardSetting(id=SETTING_ID)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def load_runtime_config(db: AsyncSession) -> AiGuardRuntimeConfig:
    row = await get_or_create_setting(db)
    return AiGuardRuntimeConfig(
        enabled=bool(row.enabled),
        provider_base_url=row.provider_base_url or "https://api.openai.com/v1",
        api_key=decrypt_secret(row.api_key_encrypted),
        model=row.model or "gpt-4o-mini",
        temperature=float(row.temperature or 0.3),
        max_tokens=int(row.max_tokens or 4096),
        chat_enabled=bool(row.chat_enabled),
        defense_enabled=bool(row.defense_enabled),
        default_apply_mode=row.default_apply_mode or "suggest_only",
        max_logs_per_analysis=int(row.max_logs_per_analysis or 200),
        analysis_cooldown_sec=int(row.analysis_cooldown_sec or 300),
        auto_block_min_confidence=float(row.auto_block_min_confidence or 0.85),
    )


async def is_defense_enabled(db: AsyncSession) -> bool:
    cfg = await load_runtime_config(db)
    return cfg.enabled and cfg.defense_enabled and bool(cfg.api_key)
