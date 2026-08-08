"""Built-in bot categories seeded on first install."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import BotCategory
from app.services.bootstrap_seed import seed_section

log = logging.getLogger("waf.bootstrap.bot_categories")

SEED_KEY = "waf:bootstrap:bot_categories_v2"

DEFAULT_CATEGORIES = seed_section("bot_categories")


async def seed_builtin_categories(db: AsyncSession) -> int:
    redis = get_redis()
    if await redis.get(SEED_KEY):
        return 0
    existing = (await db.execute(select(func.count(BotCategory.id)))).scalar_one()
    if existing:
        await redis.set(SEED_KEY, "1")
        return 0

    created = 0
    for spec in DEFAULT_CATEGORIES:
        db.add(
            BotCategory(
                value=spec["value"],
                label=spec["label"],
                sort_order=int(spec.get("sort_order") or 0),
                is_builtin=bool(spec.get("is_builtin", True)),
                remark=spec.get("remark"),
            )
        )
        created += 1

    await db.commit()
    await redis.set(SEED_KEY, "1")
    log.info("seeded %d builtin bot categories", created)
    return created


async def ensure_builtin_categories(db: AsyncSession) -> int:
    try:
        return await seed_builtin_categories(db)
    except Exception:  # noqa: BLE001
        log.exception("seed builtin bot categories failed")
        return 0
