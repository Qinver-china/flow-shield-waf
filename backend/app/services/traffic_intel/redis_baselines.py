"""Publish learned traffic baselines to Redis for engine rule matching.

Only per-site rows are published. For each site+window, prefer the current
15-minute slot; if missing (slot just rolled), fall back to the latest row so
rules/UI do not briefly lose all baselines.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models.traffic_intel import TrafficBaseline
from app.services.traffic_intel.store.baseline_mysql import slot_key_for
from app.services.traffic_intel.timezone import get_traffic_timezone, local_datetime

log = logging.getLogger("waf.traffic_intel.redis")

BASELINE_KEY = "waf:traffic:baselines"
BASELINE_TTL = 7200


async def publish_baselines_to_redis(db: AsyncSession) -> None:
    """Write per-site baselines for engine traffic rules (with slot fallback)."""
    timezone_name = await get_traffic_timezone(db)
    local_now = local_datetime(datetime.utcnow(), timezone_name)
    slot_key = slot_key_for(local_now)
    rows = (
        await db.execute(
            select(TrafficBaseline).where(TrafficBaseline.site_id.is_not(None))
        )
    ).scalars().all()

    # (site_id, window_sec) -> best row
    best: dict[tuple[int, int], TrafficBaseline] = {}
    for row in rows:
        if row.site_id is None:
            continue
        key = (int(row.site_id), int(row.window_sec))
        prev = best.get(key)
        if prev is None:
            best[key] = row
            continue
        prev_cur = prev.slot_key == slot_key
        row_cur = row.slot_key == slot_key
        if row_cur and not prev_cur:
            best[key] = row
        elif row_cur == prev_cur:
            prev_at = prev.updated_at or datetime.min
            row_at = row.updated_at or datetime.min
            if row_at >= prev_at:
                best[key] = row

    sites: dict[str, dict[str, dict]] = {}
    for (site_id, window_sec), row in best.items():
        sites.setdefault(str(site_id), {})[str(window_sec)] = {
            "avg": float(row.avg_requests),
            "samples": int(row.sample_count),
            "slot_key": row.slot_key,
            "warmup": False,
        }

    payload = {
        "updated_at": int(datetime.utcnow().timestamp()),
        "slot_key": slot_key,
        "timezone": timezone_name,
        "sites": sites,
    }
    redis = get_redis()
    await redis.set(BASELINE_KEY, json.dumps(payload), ex=BASELINE_TTL)
    log.debug(
        "published traffic baselines slot=%s site_windows=%d",
        slot_key,
        len(best),
    )
