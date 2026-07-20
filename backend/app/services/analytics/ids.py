"""Monotonic IDs for ClickHouse event tables (Redis INCR)."""
from __future__ import annotations

from app.core.redis import get_redis
from app.services.analytics.constants import (
    REDIS_SEQ_ALERT_LOG,
    REDIS_SEQ_INCIDENT,
    REDIS_SEQ_TRAFFIC_ALERT,
)


async def next_incident_id() -> int:
    redis = get_redis()
    return int(await redis.incr(REDIS_SEQ_INCIDENT))


async def next_alert_log_id() -> int:
    redis = get_redis()
    return int(await redis.incr(REDIS_SEQ_ALERT_LOG))


async def next_traffic_alert_id() -> int:
    redis = get_redis()
    return int(await redis.incr(REDIS_SEQ_TRAFFIC_ALERT))
