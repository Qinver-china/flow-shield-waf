"""Built-in bot profiles seeded on first install."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import BotProfile

log = logging.getLogger("waf.bootstrap.bots")

SEED_KEY = "waf:bootstrap:bots_v2"

DEFAULT_BOTS: list[dict] = [
    {
        "name": "Googlebot",
        "categories": ["search_engine"],
        "ua_patterns": ["Googlebot", "Google-InspectionTool"],
        "verify_dns_suffix": ".googlebot.com",
        "remark": "Google 搜索引擎爬虫",
    },
    {
        "name": "Bingbot",
        "categories": ["search_engine"],
        "ua_patterns": ["bingbot", "BingPreview"],
        "verify_dns_suffix": ".search.msn.com",
        "remark": "Microsoft Bing 爬虫",
    },
    {
        "name": "Baiduspider",
        "categories": ["search_engine"],
        "ua_patterns": ["Baiduspider", "BaiduSpider"],
        "verify_dns_suffix": ".baidu.com",
        "remark": "百度搜索引擎爬虫",
    },
    {
        "name": "Sogou Spider",
        "categories": ["search_engine"],
        "ua_patterns": ["Sogou web spider", "Sogou inst spider"],
        "remark": "搜狗搜索引擎爬虫",
    },
    {
        "name": "360Spider",
        "categories": ["search_engine"],
        "ua_patterns": ["360Spider", "HaosouSpider"],
        "remark": "360 搜索引擎爬虫",
    },
    {
        "name": "Bytespider",
        "categories": ["search_engine"],
        "ua_patterns": ["Bytespider"],
        "remark": "字节跳动爬虫",
    },
    {
        "name": "YandexBot",
        "categories": ["search_engine"],
        "ua_patterns": ["YandexBot", "YandexImages"],
        "verify_dns_suffix": ".yandex.ru",
        "remark": "Yandex 搜索引擎爬虫",
    },
    {
        "name": "facebookexternalhit",
        "categories": ["social"],
        "ua_patterns": ["facebookexternalhit", "Facebot"],
        "remark": "Facebook 链接预览",
    },
    {
        "name": "Twitterbot",
        "categories": ["social"],
        "ua_patterns": ["Twitterbot"],
        "remark": "Twitter/X 链接预览",
    },
    {
        "name": "UptimeRobot",
        "categories": ["monitoring"],
        "ua_patterns": ["UptimeRobot"],
        "remark": "UptimeRobot 可用性监控",
    },
    {
        "name": "curl",
        "categories": ["scraper"],
        "ua_patterns": ["curl/"],
        "remark": "curl 命令行工具",
    },
    {
        "name": "python-requests",
        "categories": ["scraper"],
        "ua_patterns": ["python-requests"],
        "remark": "Python requests 库",
    },
]


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
                categories=list(spec["categories"]),
                ua_patterns=spec["ua_patterns"],
                enabled=True,
                site_ids=None,
                verify_dns_suffix=spec.get("verify_dns_suffix"),
                is_builtin=True,
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
