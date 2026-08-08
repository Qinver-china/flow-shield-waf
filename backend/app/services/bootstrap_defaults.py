"""Built-in WAF policies seeded on first install.

Sources: backend/app/data/builtin_seed.json
Covers IP groups, custom rules, black/white lists, exceptions, rate limits.
Users may freely edit, disable, or delete these afterward.
Seeding is idempotent (tracked via Redis key + existing-row guards).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.fields import validate_condition
from app.models import Exception_, IpGroup, IpList, RateLimit, Rule
from app.services.bootstrap_seed import seed_section
from app.services.ip_entry import normalize_entries

log = logging.getLogger("waf.bootstrap.defaults")

SEED_KEY = "waf:bootstrap:default_policies_v2"


def _normalize_conditions(raw: dict | None) -> dict:
    if raw is None or raw == {}:
        return {"logic": "and", "conditions": []}
    return validate_condition(raw)


def _catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        "ip_groups": seed_section("ip_groups"),
        "rules": seed_section("rules"),
        "blacklist": seed_section("blacklist"),
        "whitelist": seed_section("whitelist"),
        "exceptions": seed_section("exceptions"),
        "ratelimits": seed_section("ratelimits"),
    }


# Public aliases used by tests / importers
DEFAULT_IP_GROUPS = seed_section("ip_groups")
DEFAULT_RULES = seed_section("rules")
DEFAULT_BLACKLIST = seed_section("blacklist")
DEFAULT_WHITELIST = seed_section("whitelist")
DEFAULT_EXCEPTIONS = seed_section("exceptions")
DEFAULT_RATE_LIMITS = seed_section("ratelimits")


def _validate_catalog() -> None:
    """Fail fast at import if any built-in condition / IP entry is invalid."""
    for spec in DEFAULT_IP_GROUPS:
        normalize_entries(spec.get("entries") or [])
    for spec in DEFAULT_RULES:
        _normalize_conditions(spec.get("conditions"))
        if spec.get("mode") not in ("observe", "block", "captcha", "js_challenge", "slide_captcha"):
            raise ValueError(f"invalid rule mode: {spec.get('name')}")
    for spec in [*DEFAULT_BLACKLIST, *DEFAULT_WHITELIST]:
        _normalize_conditions(spec.get("conditions"))
        if spec.get("list_type") not in ("black", "white"):
            raise ValueError(f"invalid list_type: {spec.get('name')}")
    for spec in DEFAULT_EXCEPTIONS:
        _normalize_conditions(spec.get("conditions"))
    for spec in DEFAULT_RATE_LIMITS:
        if spec.get("conditions"):
            _normalize_conditions(spec.get("conditions"))
        if int(spec.get("threshold") or 0) <= 0 or int(spec.get("window") or 0) <= 0:
            raise ValueError(f"invalid ratelimit window/threshold: {spec.get('name')}")


_validate_catalog()


async def _already_seeded(db: AsyncSession) -> bool:
    redis = get_redis()
    if await redis.get(SEED_KEY):
        return True

    counts = [
        (await db.execute(select(func.count(Rule.id)))).scalar_one(),
        (await db.execute(select(func.count(RateLimit.id)))).scalar_one(),
        (await db.execute(select(func.count(IpList.id)))).scalar_one(),
        (await db.execute(select(func.count(Exception_.id)))).scalar_one(),
        (await db.execute(select(func.count(IpGroup.id)))).scalar_one(),
    ]
    if any(counts):
        await redis.set(SEED_KEY, "1")
        log.info(
            "builtin policies already present (rules=%s ratelimits=%s lists=%s exceptions=%s ip_groups=%s), marking seeded",
            *counts,
        )
        return True
    return False


async def seed_default_policies(db: AsyncSession) -> int:
    """Insert built-in policies once. Returns number of rows created."""
    if await _already_seeded(db):
        return 0

    catalog = _catalog()
    created = 0

    for spec in catalog["ip_groups"]:
        db.add(
            IpGroup(
                name=spec["name"],
                remark=spec.get("remark"),
                entries=normalize_entries(spec.get("entries") or []),
            )
        )
        created += 1

    for spec in catalog["rules"]:
        db.add(
            Rule(
                name=spec["name"],
                site_ids=spec.get("site_ids"),
                priority=int(spec.get("priority", 100)),
                mode=spec.get("mode", "block"),
                enabled=bool(spec.get("enabled", True)),
                conditions=_normalize_conditions(spec.get("conditions")),
                remark=spec.get("remark"),
                custom_block_page_enabled=bool(spec.get("custom_block_page_enabled", False)),
                block_page_status_code=spec.get("block_page_status_code"),
                block_page_html=spec.get("block_page_html"),
            )
        )
        created += 1

    for spec in [*catalog["blacklist"], *catalog["whitelist"]]:
        db.add(
            IpList(
                list_type=spec["list_type"],
                name=spec["name"],
                site_ids=spec.get("site_ids"),
                enabled=bool(spec.get("enabled", True)),
                conditions=_normalize_conditions(spec.get("conditions")),
                remark=spec.get("remark"),
                expire_at=None,
                custom_block_page_enabled=bool(spec.get("custom_block_page_enabled", False)),
                block_page_status_code=spec.get("block_page_status_code"),
                block_page_html=spec.get("block_page_html"),
            )
        )
        created += 1

    for spec in catalog["exceptions"]:
        db.add(
            Exception_(
                name=spec["name"],
                site_ids=spec.get("site_ids"),
                scope=spec.get("scope") or "all",
                enabled=bool(spec.get("enabled", True)),
                conditions=_normalize_conditions(spec.get("conditions")),
                remark=spec.get("remark"),
            )
        )
        created += 1

    for spec in catalog["ratelimits"]:
        conditions = spec.get("conditions")
        db.add(
            RateLimit(
                name=spec["name"],
                site_ids=spec.get("site_ids"),
                priority=int(spec.get("priority", 100)),
                enabled=bool(spec.get("enabled", True)),
                keys=spec.get("keys") or [{"field": "ip.src"}],
                window=int(spec.get("window", 60)),
                threshold=int(spec.get("threshold", 100)),
                mode=spec.get("mode", "block"),
                conditions=_normalize_conditions(conditions) if conditions else None,
                remark=spec.get("remark"),
                custom_block_page_enabled=bool(spec.get("custom_block_page_enabled", False)),
                block_page_status_code=spec.get("block_page_status_code"),
                block_page_html=spec.get("block_page_html"),
            )
        )
        created += 1

    await db.commit()
    await get_redis().set(SEED_KEY, "1")
    log.info(
        "seeded %d builtin policies (ip_groups=%d rules=%d lists=%d exceptions=%d ratelimits=%d)",
        created,
        len(catalog["ip_groups"]),
        len(catalog["rules"]),
        len(catalog["blacklist"]) + len(catalog["whitelist"]),
        len(catalog["exceptions"]),
        len(catalog["ratelimits"]),
    )
    return created


async def ensure_default_policies(db: AsyncSession) -> int:
    """Called from application bootstrap."""
    try:
        return await seed_default_policies(db)
    except Exception:  # noqa: BLE001
        log.exception("seed default policies failed")
        return 0
