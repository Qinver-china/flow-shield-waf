"""Ingest engine Redis snapshots into durable ClickHouse rollups.

Only per-site windows are persisted. Snapshot ``global`` is a derived sum and
must not be written as site_id=NULL history.
"""
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

    # Keep global_windows as the derived sum for API/overview readers only.
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

    site_windows: dict[int, list[WindowSample]] = {}
    for site_key, site_data in (data.get("sites") or {}).items():
        try:
            site_id = int(site_key)
        except (TypeError, ValueError):
            continue
        samples: list[WindowSample] = []
        for w in site_data.get("windows") or []:
            try:
                samples.append(
                    WindowSample(
                        window_sec=int(w["sec"]),
                        requests=int(w.get("requests") or 0),
                        qps=float(w.get("qps") or 0),
                        site_id=site_id,
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        if samples:
            site_windows[site_id] = samples

    return TrafficSnapshot(
        updated_at=int(data.get("updated_at") or 0),
        global_windows=windows,
        burst_active=bool(data.get("global", {}).get("burst_active")),
        site_windows=site_windows,
    )


class SnapshotIngestor:
    """Read live snapshot → persist per-site minute rollup + window history."""

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
        analysis_samples: list[WindowSample] = []
        sites_written = 0

        for site_id, site_samples in snapshot.site_windows.items():
            site_minute = 0
            for w in site_samples:
                if w.window_sec == 60:
                    site_minute = w.requests
                if w.window_sec in ANALYSIS_WINDOWS_SEC:
                    analysis_samples.append(
                        WindowSample(
                            window_sec=w.window_sec,
                            requests=w.requests,
                            qps=w.qps,
                            site_id=site_id,
                            observed_at=now,
                        )
                    )
            if site_minute > 0:
                await asyncio.to_thread(
                    self._store.insert_minute, now, site_minute, site_id=site_id
                )
                sites_written += 1

        if analysis_samples:
            await asyncio.to_thread(
                self._store.insert_window_snapshots, now, analysis_samples
            )
            log.debug(
                "ingested traffic minute=%s site_minutes=%d windows=%d sites=%d",
                now.isoformat(),
                sites_written,
                len(analysis_samples),
                len(snapshot.site_windows),
            )
        return snapshot
