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

log = logging.getLogger("waf.traffic_intel.redis")

BASELINE_KEY = "waf:traffic:baselines"
BASELINE_TTL = 7200


async def publish_baselines_to_redis(db: AsyncSession) -> None:
    """Write current-hour global baselines for engine traffic rule conditions."""
    slot_key = slot_key_for(datetime.utcnow())
    rows = (
        await db.execute(
            select(TrafficBaseline).where(
                TrafficBaseline.site_id.is_(None),
                TrafficBaseline.slot_key == slot_key,
            )
        )
    ).scalars().all()

    windows: dict[str, dict] = {}
    for row in rows:
        windows[str(row.window_sec)] = {
            "avg": float(row.avg_requests),
            "samples": int(row.sample_count),
        }

    payload = {
        "updated_at": int(datetime.utcnow().timestamp()),
        "slot_key": slot_key,
        "global": windows,
    }
    redis = get_redis()
    await redis.set(BASELINE_KEY, json.dumps(payload), ex=BASELINE_TTL)
    log.debug("published traffic baselines slot=%s windows=%d", slot_key, len(windows))
