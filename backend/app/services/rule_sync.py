"""Build the runtime WAF config from the database and publish it to Redis.

The backend is the single source of truth. On every change we serialize the
whole config to `waf:config` (JSON) and bump `waf:config:version`; the engine
workers poll the version and hot-reload the rule set (no nginx reload needed).
Only site topology changes require an nginx reload (see nginx_conf.py).
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import BotCategory, BotProfile, Exception_, IpGroup, IpList, RateLimit, Rule, Site
from app.services import waf_settings
from app.services.site_scope import resolved_site_ids
from app.services.site_domains import site_domain_list
from app.services.traffic_intel.redis_baselines import publish_baselines_to_redis
from app.constants.response_pages import (
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
    DEFAULT_CAPTCHA_FOOTER_HTML,
)

log = logging.getLogger("waf.rule_sync")

CONFIG_KEY = "waf:config"
STAGING_KEY = "waf:config:staging"
VERSION_KEY = "waf:config:version"
DIRTY_KEY = "waf:config:dirty"


def _base(row) -> dict:
    item: dict = {
        "id": row.id,
        "name": row.name,
        "enabled": row.enabled,
        "conditions": row.conditions or {"logic": "and", "conditions": []},
    }
    site_ids = resolved_site_ids(row)
    if site_ids:
        item["site_ids"] = site_ids
    return item


def _site_item(site) -> dict:
    domains = site_domain_list(site)
    item = {
        "id": site.id,
        "domain": site.domain,
        "domains": domains,
        "enabled": site.enabled,
    }
    if site.custom_block_page_enabled:
        item["block_page"] = {
            "enabled": True,
            "status_code": site.block_page_status_code or DEFAULT_BLOCK_PAGE_STATUS,
            "html": site.block_page_html or DEFAULT_BLOCK_PAGE_HTML,
        }
    if site.custom_captcha_footer_enabled:
        item["captcha_footer"] = {
            "enabled": True,
            "html": site.captcha_footer_html or DEFAULT_CAPTCHA_FOOTER_HTML,
        }
    return item


async def build_config(db: AsyncSession) -> dict:
    sites = (await db.execute(select(Site))).scalars().all()
    rules = (await db.execute(select(Rule))).scalars().all()
    lists = (await db.execute(select(IpList))).scalars().all()
    exceptions = (await db.execute(select(Exception_))).scalars().all()
    ratelimits = (await db.execute(select(RateLimit))).scalars().all()
    ip_groups = (await db.execute(select(IpGroup))).scalars().all()
    bots = (await db.execute(select(BotProfile))).scalars().all()
    bot_categories = (await db.execute(select(BotCategory))).scalars().all()

    whitelist, blacklist = [], []
    for row in lists:
        item = _base(row)
        (whitelist if row.list_type == "white" else blacklist).append(item)

    rule_items = []
    for r in rules:
        it = _base(r)
        it["priority"] = r.priority
        it["mode"] = r.mode
        rule_items.append(it)

    exc_items = []
    for e in exceptions:
        it = _base(e)
        it["scope"] = e.scope
        exc_items.append(it)

    rl_items = []
    for rl in ratelimits:
        it = {
            "id": rl.id,
            "name": rl.name,
            "priority": rl.priority,
            "enabled": rl.enabled,
            "keys": rl.keys or [{"field": "ip.src"}],
            "window": rl.window,
            "threshold": rl.threshold,
            "mode": rl.mode,
        }
        site_ids = resolved_site_ids(rl)
        if site_ids:
            it["site_ids"] = site_ids
        if rl.conditions:
            it["conditions"] = rl.conditions
        rl_items.append(it)

    settings_cfg = await waf_settings.get_runtime_settings(db)

    ip_group_map = {
        str(g.id): {
            "id": g.id,
            "name": g.name,
            "entries": g.entries or [],
        }
        for g in ip_groups
    }

    bot_items = []
    for b in bots:
        it = {
            "id": b.id,
            "name": b.name,
            "category": b.category,
            "ua_patterns": b.ua_patterns or [],
            "enabled": b.enabled,
            "verify_dns_suffix": b.verify_dns_suffix,
        }
        site_ids = resolved_site_ids(b)
        if site_ids:
            it["site_ids"] = site_ids
        bot_items.append(it)

    return {
        "sites": [_site_item(s) for s in sites],
        "rules": rule_items,
        "whitelist": whitelist,
        "blacklist": blacklist,
        "exceptions": exc_items,
        "ratelimits": rl_items,
        "ip_groups": ip_group_map,
        "bots": bot_items,
        "bot_category_values": sorted(c.value for c in bot_categories),
        "settings": settings_cfg,
    }


async def publish(db: AsyncSession) -> int:
    """Rebuild config and bump version. Returns the new version."""
    config = await build_config(db)
    redis = get_redis()
    payload = json.dumps(config, ensure_ascii=False)
    try:
        pipe = redis.pipeline()
        pipe.set(STAGING_KEY, payload)
        pipe.rename(STAGING_KEY, CONFIG_KEY)
        pipe.incr(VERSION_KEY)
        results = await pipe.execute()
        version = int(results[-1])
        await redis.delete(DIRTY_KEY)
    except Exception:
        await redis.set(DIRTY_KEY, "1")
        raise
    try:
        await publish_baselines_to_redis(db)
    except Exception:  # noqa: BLE001
        log.exception("publish traffic baselines failed")
    log.info("published waf config version=%s rules=%s", version, len(config["rules"]))
    return version


async def retry_if_dirty(db: AsyncSession) -> int | None:
    """Republish when a previous publish failed after DB commit."""
    redis = get_redis()
    if not await redis.get(DIRTY_KEY):
        return None
    log.warning("retrying dirty waf config publish")
    return await publish(db)
