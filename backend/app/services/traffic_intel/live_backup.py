"""Persist / restore live traffic window state (Redis primary, SQLite backup).

Panel and alert evaluation always read Redis. SQLite is only for disaster recovery
when Redis has no traffic keys (e.g. volume wiped).

Backup payload is per-site sparse minute rings only. Snapshot ``global`` is rebuilt
as the sum of site windows on restore (never stored as a separate series).
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.redis import get_redis
from app.models.traffic_live_backup import (
    BACKUP_INTERVAL_SEC,
    BACKUP_WINDOW_SECS,
    REDIS_MIN_S_PREFIX,
    REDIS_SNAPSHOT_KEY,
    TrafficLiveBackup,
)

log = logging.getLogger("waf.traffic_live_backup")

_BACKUP_ID = 1


def _compact_minutes(raw: dict | list | None) -> dict[str, int]:
    """Keep only positive minute counts (sparse)."""
    if not raw:
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n > 0:
            out[str(int(k))] = n
    return out


def _sum_window_from_minutes(minutes: dict[str, int], window_sec: int, now_ts: int) -> int:
    minute_start = now_ts - (now_ts % 60)
    need = max(1, (window_sec + 59) // 60)
    total = 0
    for i in range(need):
        m = minute_start - i * 60
        total += int(minutes.get(str(m), 0) or 0)
    return total


def _windows_from_minutes(minutes: dict[str, int], now_ts: int) -> list[dict]:
    windows: list[dict] = []
    for sec in BACKUP_WINDOW_SECS:
        req = _sum_window_from_minutes(minutes, sec, now_ts)
        windows.append({"sec": sec, "requests": req, "qps": req / max(sec, 1)})
    # Schema compat: 10s is live-only and always 0 after cold restore.
    windows.insert(0, {"sec": 10, "requests": 0, "qps": 0.0})
    return windows


def _sum_windows(site_windows: list[list[dict]]) -> list[dict]:
    """Merge per-site window rows by sec (requests sum, qps recomputed)."""
    by_sec: dict[int, int] = {}
    order: list[int] = []
    for windows in site_windows:
        for w in windows:
            try:
                sec = int(w.get("sec") or 0)
                req = int(w.get("requests") or 0)
            except (TypeError, ValueError):
                continue
            if sec <= 0:
                continue
            if sec not in by_sec:
                order.append(sec)
                by_sec[sec] = 0
            by_sec[sec] += req
    return [
        {"sec": sec, "requests": by_sec[sec], "qps": by_sec[sec] / max(sec, 1)}
        for sec in order
    ]


async def flush_backup_once() -> None:
    redis = get_redis()
    now_ts = int(datetime.utcnow().timestamp())
    site_ids: set[str] = set()

    raw = await redis.get(REDIS_SNAPSHOT_KEY)
    if raw:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        try:
            snap = json.loads(raw)
            now_ts = int(snap.get("updated_at") or now_ts)
            site_ids.update(str(k) for k in (snap.get("sites") or {}).keys())
        except (json.JSONDecodeError, TypeError):
            pass

    if not site_ids:
        async for key in redis.scan_iter(match=f"{REDIS_MIN_S_PREFIX}*", count=100):
            k = key.decode() if isinstance(key, bytes) else str(key)
            sid = k[len(REDIS_MIN_S_PREFIX) :]
            if sid:
                site_ids.add(sid)

    sites_out: dict[str, dict] = {}
    for site_key in site_ids:
        min_s = _compact_minutes(await redis.hgetall(f"{REDIS_MIN_S_PREFIX}{site_key}"))
        if min_s:
            sites_out[str(site_key)] = {"m": min_s}

    if not sites_out:
        return

    body = json.dumps(
        {"ts": now_ts, "s": sites_out},
        separators=(",", ":"),
    )

    async with SessionLocal() as db:
        row = (
            await db.execute(select(TrafficLiveBackup).where(TrafficLiveBackup.id == _BACKUP_ID))
        ).scalar_one_or_none()
        if row is None:
            row = TrafficLiveBackup(id=_BACKUP_ID, payload=body, updated_at=datetime.utcnow())
            db.add(row)
        else:
            row.payload = body
            row.updated_at = datetime.utcnow()
        await db.commit()
    log.debug("traffic live backup flushed (%d bytes)", len(body))


async def restore_redis_if_empty() -> bool:
    """If Redis has no site minute ring / snapshot, reload from SQLite backup.

    Returns True when a restore was applied.
    """
    redis = get_redis()
    # Any site minute key or snapshot means Redis already has live state.
    async for _ in redis.scan_iter(match=f"{REDIS_MIN_S_PREFIX}*", count=1):
        return False
    if await redis.exists(REDIS_SNAPSHOT_KEY):
        return False

    async with SessionLocal() as db:
        row = (
            await db.execute(select(TrafficLiveBackup).where(TrafficLiveBackup.id == _BACKUP_ID))
        ).scalar_one_or_none()
        if row is None or not row.payload:
            return False
        try:
            data = json.loads(row.payload)
        except (json.JSONDecodeError, TypeError):
            log.warning("traffic live backup payload corrupt")
            return False

    now_ts = int(data.get("ts") or datetime.utcnow().timestamp())
    pipe = redis.pipeline(transaction=False)

    sites_out: dict[str, dict] = {}
    site_window_lists: list[list[dict]] = []
    # New format: s only. Old format may still have g (ignored for storage).
    for site_key, site in (data.get("s") or {}).items():
        min_s = {str(k): int(v) for k, v in (site.get("m") or {}).items()}
        if not min_s:
            continue
        min_key = f"{REDIS_MIN_S_PREFIX}{site_key}"
        for minute, count in min_s.items():
            pipe.hset(min_key, str(minute), int(count))
        windows = _windows_from_minutes(min_s, now_ts)
        sites_out[str(site_key)] = {"windows": windows}
        site_window_lists.append(windows)

    if not sites_out and (data.get("g") or {}).get("m"):
        # Legacy backup with only global minutes: cannot attribute to sites — skip.
        log.warning("legacy global-only traffic backup ignored (site-only restore required)")
        return False

    snapshot = {
        "updated_at": now_ts,
        "global": {
            "windows": _sum_windows(site_window_lists),
            "burst_active": False,
        },
        "sites": sites_out,
    }
    pipe.set(REDIS_SNAPSHOT_KEY, json.dumps(snapshot), ex=120)
    await pipe.execute()
    log.info(
        "restored traffic live state from sqlite backup (sites=%d)",
        len(sites_out),
    )
    return True


async def run_traffic_live_backup_loop(stop_event=None) -> None:
    await restore_redis_if_empty()
    log.info("traffic live backup loop started (interval=%ss)", BACKUP_INTERVAL_SEC)
    while stop_event is None or not stop_event.is_set():
        try:
            await flush_backup_once()
        except Exception:  # noqa: BLE001
            log.exception("traffic live backup flush failed")
        if stop_event is not None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=BACKUP_INTERVAL_SEC)
                break
            except TimeoutError:
                continue
        else:
            await asyncio.sleep(BACKUP_INTERVAL_SEC)
