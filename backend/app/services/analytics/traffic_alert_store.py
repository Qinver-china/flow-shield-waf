"""ClickHouse store for traffic anomaly alerts."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.clickhouse import get_clickhouse, get_clickhouse_ingest
from app.services.analytics.constants import CH_TRAFFIC_ALERTS_TABLE
from app.services.analytics.ids import next_traffic_alert_id
from app.services.traffic_intel.types import AlertStatus, AnomalyResult

log = logging.getLogger("waf.analytics.traffic_alerts")

_COLUMNS = [
    "id",
    "site_id",
    "window_sec",
    "current_requests",
    "baseline_avg",
    "deviation_ratio",
    "severity",
    "status",
    "message",
    "detected_at",
    "created_at",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class TrafficAlertRecord:
    id: int
    site_id: int | None
    window_sec: int
    current_requests: int
    baseline_avg: float
    deviation_ratio: float
    severity: str
    status: str
    message: str
    detected_at: datetime
    created_at: datetime | None = None


class TrafficAlertStore:
    async def create(self, anomaly: AnomalyResult) -> TrafficAlertRecord:
        now = _utcnow()
        row_id = await next_traffic_alert_id()
        rec = TrafficAlertRecord(
            id=row_id,
            site_id=anomaly.site_id,
            window_sec=anomaly.window_sec,
            current_requests=anomaly.current_requests,
            baseline_avg=anomaly.baseline_avg,
            deviation_ratio=anomaly.deviation_ratio,
            severity=anomaly.severity.value,
            status=AlertStatus.OPEN.value,
            message=anomaly.message,
            detected_at=anomaly.detected_at,
            created_at=now,
        )
        await self._insert(rec)
        return rec

    async def recent_open_count(
        self,
        *,
        site_id: int | None,
        window_sec: int,
        within_sec: int,
    ) -> int:
        since = _utcnow() - timedelta(seconds=within_sec)

        def _query():
            client = get_clickhouse()
            if site_id is None:
                site_clause = "site_id IS NULL"
                params = {
                    "window_sec": int(window_sec),
                    "since": since,
                    "status": AlertStatus.OPEN.value,
                }
            else:
                site_clause = "site_id = {site_id:UInt32}"
                params = {
                    "site_id": int(site_id),
                    "window_sec": int(window_sec),
                    "since": since,
                    "status": AlertStatus.OPEN.value,
                }
            rows = client.query(
                f"""
                SELECT count()
                FROM {CH_TRAFFIC_ALERTS_TABLE}
                WHERE {site_clause}
                  AND window_sec = {{window_sec:UInt32}}
                  AND status = {{status:String}}
                  AND detected_at >= {{since:DateTime64(3)}}
                """,
                parameters=params,
            ).result_rows
            return int(rows[0][0]) if rows else 0

        return await asyncio.to_thread(_query)

    async def list_recent(
        self,
        *,
        limit: int = 50,
        site_id: int | None = None,
    ) -> list[TrafficAlertRecord]:
        def _query():
            client = get_clickhouse()
            where = ""
            params: dict = {"limit": int(limit)}
            if site_id is not None:
                where = "WHERE site_id = {site_id:UInt32}"
                params["site_id"] = int(site_id)
            rows = client.query(
                f"""
                SELECT
                  id, site_id, window_sec, current_requests, baseline_avg,
                  deviation_ratio, severity, status, message, detected_at, created_at
                FROM {CH_TRAFFIC_ALERTS_TABLE}
                {where}
                ORDER BY detected_at DESC, id DESC
                LIMIT {{limit:UInt32}}
                """,
                parameters=params,
            ).result_rows
            return [
                TrafficAlertRecord(
                    id=int(r[0]),
                    site_id=int(r[1]) if r[1] is not None else None,
                    window_sec=int(r[2]),
                    current_requests=int(r[3]),
                    baseline_avg=float(r[4]),
                    deviation_ratio=float(r[5]),
                    severity=str(r[6]),
                    status=str(r[7]),
                    message=str(r[8]),
                    detected_at=r[9],
                    created_at=r[10],
                )
                for r in rows
            ]

        return await asyncio.to_thread(_query)

    async def _insert(self, rec: TrafficAlertRecord) -> None:
        row = [
            rec.id,
            rec.site_id,
            rec.window_sec,
            rec.current_requests,
            rec.baseline_avg,
            rec.deviation_ratio,
            rec.severity,
            rec.status,
            rec.message,
            rec.detected_at,
            rec.created_at or _utcnow(),
        ]

        def _write():
            get_clickhouse_ingest().insert(CH_TRAFFIC_ALERTS_TABLE, [row], column_names=_COLUMNS)

        await asyncio.to_thread(_write)
