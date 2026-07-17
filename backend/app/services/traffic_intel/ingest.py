"""Ingest engine Redis snapshots into durable ClickHouse rollups."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from app.core.redis import get_redis
from app.services.traffic_intel.constants import ANALYSIS_WINDOWS_SEC, REDIS_SNAPSHOT_KEY
from app.services.traffic_intel.store.clickhouse import ClickHouseTrafficStore
from app.services.traffic_intel.types import TrafficSnapshot, WindowSample

log = logging.getLogger("waf.traffic_intel.ingest")


def parse_snapshot(raw: str | bytes) -> TrafficSnapshot | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    windows = []
    for w in data.get("global", {}).get("windows") or []:
        try:
            windows.append(
                WindowSample(
                    window_sec=int(w["sec"]),
                    requests=int(w.get("requests") or 0),
                    qps=float(w.get("qps") or 0),
                    site_id=None,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return TrafficSnapshot(
        updated_at=int(data.get("updated_at") or 0),
        global_windows=windows,
        burst_active=bool(data.get("global", {}).get("burst_active")),
    )


class SnapshotIngestor:
    """Read live snapshot → persist minute rollup + window history."""

    def __init__(self, store: ClickHouseTrafficStore | None = None):
        self._store = store or ClickHouseTrafficStore()

    async def ingest_once(self) -> TrafficSnapshot | None:
        redis = get_redis()
        raw = await redis.get(REDIS_SNAPSHOT_KEY)
        if not raw:
            log.debug("no traffic snapshot in redis")
            return None

        snapshot = parse_snapshot(raw)
        if snapshot is None:
            log.warning("invalid traffic snapshot payload")
            return None

        now = datetime.utcnow().replace(second=0, microsecond=0)
        minute_requests = 0
        analysis_samples: list[WindowSample] = []

        for w in snapshot.global_windows:
            if w.window_sec == 60:
                minute_requests = w.requests
            if w.window_sec in ANALYSIS_WINDOWS_SEC:
                analysis_samples.append(
                    WindowSample(
                        window_sec=w.window_sec,
                        requests=w.requests,
                        qps=w.qps,
                        site_id=None,
                        observed_at=now,
                    )
                )

        if minute_requests > 0:
            await asyncio.to_thread(
                self._store.insert_minute, now, minute_requests, site_id=None
            )
        if analysis_samples:
            await asyncio.to_thread(
                self._store.insert_window_snapshots, now, analysis_samples
            )
            log.debug(
                "ingested traffic minute=%s requests=%d windows=%d",
                now.isoformat(),
                minute_requests,
                len(analysis_samples),
            )
        return snapshot
