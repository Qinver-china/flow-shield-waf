"""Build request / origin timelines from Redis per-site minute rings."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.constants.traffic_timeline import (
    TRAFFIC_TIMELINE_BUCKETS_SEC,
    TRAFFIC_TIMELINE_BUCKET_LABELS,
    TRAFFIC_TIMELINE_HOURS,
)
from app.core.redis import get_redis
from app.models.traffic_live_backup import REDIS_MIN_O_PREFIX, REDIS_MIN_S_PREFIX, REDIS_SNAPSHOT_KEY


def _parse_hash(raw: dict | None) -> dict[int, int]:
    if not raw:
        return {}
    out: dict[int, int] = {}
    for key, value in raw.items():
        k = key.decode() if isinstance(key, bytes) else str(key)
        v = value.decode() if isinstance(value, bytes) else value
        try:
            minute = int(k)
            count = int(v)
        except (TypeError, ValueError):
            continue
        if count > 0:
            out[minute] = out.get(minute, 0) + count
    return out


def _merge_minute_maps(target: dict[int, int], source: dict[int, int]) -> None:
    for minute, count in source.items():
        target[minute] = target.get(minute, 0) + count


def _sum_bucket(minutes: dict[int, int], bucket_start: int, bucket_sec: int) -> int:
    total = 0
    for minute in range(bucket_start, bucket_start + bucket_sec, 60):
        total += int(minutes.get(minute, 0) or 0)
    return total


def iter_timeline_bucket_starts(
    *,
    bucket_sec: int,
    end_ts: int,
    start_ts: int | None = None,
    hours: int | None = None,
) -> list[int]:
    """Return ascending UTC bucket start timestamps (seconds) for a trailing window."""
    if bucket_sec not in TRAFFIC_TIMELINE_BUCKETS_SEC:
        raise ValueError(f"unsupported bucket_sec: {bucket_sec}")

    end_minute = end_ts - (end_ts % 60)
    if start_ts is not None:
        start_minute = start_ts - (start_ts % 60)
    else:
        if hours is None:
            raise ValueError("hours or start_ts is required")
        minute_span = max(1, int(hours) * 60)
        start_minute = end_minute - (minute_span - 1) * 60

    first_bucket = (start_minute // bucket_sec) * bucket_sec
    bucket_starts: list[int] = []
    bucket_start = first_bucket
    while bucket_start <= end_minute:
        bucket_starts.append(bucket_start)
        bucket_start += bucket_sec
    return bucket_starts


def build_timeline_points(
    requests: dict[int, int],
    origins: dict[int, int],
    *,
    hours: int = TRAFFIC_TIMELINE_HOURS,
    bucket_sec: int = 60,
    now_ts: int | None = None,
) -> list[dict]:
    """Return ascending timeline buckets for the trailing ``hours`` window."""
    now_ts = int(now_ts or datetime.now(timezone.utc).timestamp())
    return [
        {
            "ts": bucket_start,
            "requests": _sum_bucket(requests, bucket_start, bucket_sec),
            "origin_requests": _sum_bucket(origins, bucket_start, bucket_sec),
        }
        for bucket_start in iter_timeline_bucket_starts(
            bucket_sec=bucket_sec,
            end_ts=now_ts,
            hours=hours,
        )
    ]


async def _site_ids_for_scope(site_id: int | None) -> list[str]:
    if site_id is not None:
        return [str(site_id)]

    redis = get_redis()
    site_ids: set[str] = set()
    raw = await redis.get(REDIS_SNAPSHOT_KEY)
    if raw:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
            site_ids.update(str(k) for k in (data.get("sites") or {}).keys())
        except (json.JSONDecodeError, TypeError):
            pass

    if not site_ids:
        async for key in redis.scan_iter(match=f"{REDIS_MIN_S_PREFIX}*", count=100):
            k = key.decode() if isinstance(key, bytes) else str(key)
            sid = k[len(REDIS_MIN_S_PREFIX) :]
            if sid:
                site_ids.add(sid)
        async for key in redis.scan_iter(match=f"{REDIS_MIN_O_PREFIX}*", count=100):
            k = key.decode() if isinstance(key, bytes) else str(key)
            sid = k[len(REDIS_MIN_O_PREFIX) :]
            if sid:
                site_ids.add(sid)
    return sorted(site_ids, key=lambda x: int(x))


async def load_minute_maps(site_id: int | None) -> tuple[dict[int, int], dict[int, int]]:
    redis = get_redis()
    requests: dict[int, int] = {}
    origins: dict[int, int] = {}
    for sid in await _site_ids_for_scope(site_id):
        req_raw = await redis.hgetall(f"{REDIS_MIN_S_PREFIX}{sid}")
        origin_raw = await redis.hgetall(f"{REDIS_MIN_O_PREFIX}{sid}")
        _merge_minute_maps(requests, _parse_hash(req_raw))
        _merge_minute_maps(origins, _parse_hash(origin_raw))
    return requests, origins


async def timeline_series(
    *,
    site_id: int | None = None,
    hours: int = TRAFFIC_TIMELINE_HOURS,
    bucket_sec: int = 60,
) -> dict:
    if hours != TRAFFIC_TIMELINE_HOURS:
        raise ValueError("only 24h timeline is supported")
    requests, origins = await load_minute_maps(site_id)
    return {
        "hours": hours,
        "bucket_sec": bucket_sec,
        "bucket_label": TRAFFIC_TIMELINE_BUCKET_LABELS.get(bucket_sec, f"{bucket_sec}s"),
        "site_id": site_id,
        "points": build_timeline_points(
            requests,
            origins,
            hours=hours,
            bucket_sec=bucket_sec,
        ),
    }
