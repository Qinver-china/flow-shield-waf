"""Built-in bot categories seeded on first install."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import BotCategory

log = logging.getLogger("waf.bootstrap.bot_categories")

SEED_KEY = "waf:bootstrap:bot_categories_v1"

DEFAULT_CATEGORIES: list[dict] = [
    {"value": "search_engine", "label": "搜索引擎", "sort_order": 10},
    {"value": "monitoring", "label": "监控探测", "sort_order": 20},
    {"value": "social", "label": "社交平台", "sort_order": 30},
    {"value": "seo_tool", "label": "SEO 工具", "sort_order": 40},
    {"value": "scraper", "label": "通用爬虫", "sort_order": 50},
    {"value": "malicious", "label": "恶意 Bot", "sort_order": 60},
    {"value": "other", "label": "其他", "sort_order": 99},
]


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
                sort_order=spec.get("sort_order", 0),
                is_builtin=True,
                remark=None,
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
