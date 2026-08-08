"""Built-in bot profiles seeded on first install."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import BotProfile
from app.services.bootstrap_seed import seed_section

log = logging.getLogger("waf.bootstrap.bots")

SEED_KEY = "waf:bootstrap:bots_v3"

DEFAULT_BOTS = seed_section("bots")


async def seed_builtin_bots(db: AsyncSession) -> int:
    redis = get_redis()
    if await redis.get(SEED_KEY):
        return 0
    existing = (await db.execute(select(func.count(BotProfile.id)))).scalar_one()
    if existing:
        await redis.set(SEED_KEY, "1")
        return 0

    created = 0
    for spec in DEFAULT_BOTS:
        db.add(
            BotProfile(
                name=spec["name"],
                categories=list(spec.get("categories") or []),
                ua_patterns=list(spec.get("ua_patterns") or []),
                enabled=bool(spec.get("enabled", True)),
                site_ids=spec.get("site_ids"),
                verify_dns_suffix=spec.get("verify_dns_suffix"),
                is_builtin=bool(spec.get("is_builtin", False)),
                remark=spec.get("remark"),
            )
        )
        created += 1

    await db.commit()
    await redis.set(SEED_KEY, "1")
    log.info("seeded %d builtin bot profiles", created)
    return created


async def ensure_builtin_bots(db: AsyncSession) -> int:
    try:
        return await seed_builtin_bots(db)
    except Exception:  # noqa: BLE001
        log.exception("seed builtin bots failed")
        return 0
