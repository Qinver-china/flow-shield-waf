"""Publish learned traffic baselines to Redis for engine rule matching."""
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
    """Write current-slot global + per-site baselines for engine traffic rules."""
    timezone_name = await get_traffic_timezone(db)
    local_now = local_datetime(datetime.utcnow(), timezone_name)
    slot_key = slot_key_for(local_now)
    rows = (
        await db.execute(
            select(TrafficBaseline).where(TrafficBaseline.slot_key == slot_key)
        )
    ).scalars().all()

    global_windows: dict[str, dict] = {}
    sites: dict[str, dict[str, dict]] = {}
    for row in rows:
        entry = {
            "avg": float(row.avg_requests),
            "samples": int(row.sample_count),
        }
        key = str(row.window_sec)
        if row.site_id is None:
            global_windows[key] = entry
        else:
            site_key = str(row.site_id)
            sites.setdefault(site_key, {})[key] = entry

    payload = {
        "updated_at": int(datetime.utcnow().timestamp()),
        "slot_key": slot_key,
        "timezone": timezone_name,
        "global": global_windows,
        "sites": sites,
    }
    redis = get_redis()
    await redis.set(BASELINE_KEY, json.dumps(payload), ex=BASELINE_TTL)
    log.debug(
        "published traffic baselines slot=%s global=%d sites=%d",
        slot_key,
        len(global_windows),
        len(sites),
    )
