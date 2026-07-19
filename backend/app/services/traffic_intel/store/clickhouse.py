"""ClickHouse persistence for traffic rollups and historical queries."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.core.clickhouse import get_clickhouse, get_clickhouse_ingest
from app.services.traffic_intel.constants import (
    CH_MINUTE_TABLE,
    CH_WINDOW_SNAPSHOT_TABLE,
)
from app.services.traffic_intel.timezone import local_datetime
from app.services.traffic_intel.types import WindowSample


def _slot_filters(slot_mode: str, local_minute: str) -> str:
    if slot_mode == "quarter":
        return (
            f"AND toDayOfWeek({local_minute}) = {{dow:UInt8}} "
            f"AND toHour({local_minute}) = {{hour:UInt8}} "
            f"AND intDiv(toMinute({local_minute}), 15) = {{quarter:UInt8}}"
        )
    if slot_mode == "hour":
        return (
            f"AND toDayOfWeek({local_minute}) = {{dow:UInt8}} "
            f"AND toHour({local_minute}) = {{hour:UInt8}}"
        )
    if slot_mode == "hour_only":
        return f"AND toHour({local_minute}) = {{hour:UInt8}}"
    raise ValueError(f"unsupported baseline slot mode: {slot_mode}")


def _bucket_expr(window_sec: int) -> str:
    if window_sec == 60:
        return "toStartOfMinute(minute)"
    if window_sec == 300:
        return "toStartOfFiveMinute(minute)"
    if window_sec == 1800:
        return "toStartOfInterval(minute, INTERVAL 30 MINUTE)"
    if window_sec == 3600:
        return "toStartOfHour(minute)"
    raise ValueError(f"unsupported analysis window: {window_sec}")


class ClickHouseTrafficStore:
    """Minute rollups + window snapshots in ClickHouse."""

    def ensure_schema(self) -> None:
        client = get_clickhouse()
        client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {CH_WINDOW_SNAPSHOT_TABLE} (
              ts DateTime,
              site_id Nullable(UInt32),
              window_sec UInt32,
              requests UInt64,
              qps Float64
            )
            ENGINE = MergeTree
            ORDER BY (site_id, window_sec, ts)
            TTL ts + INTERVAL 90 DAY
            SETTINGS allow_nullable_key = 1
            """
        )

    def insert_minute(
        self,
        minute: datetime,
        requests: int,
        *,
        site_id: int | None = None,
    ) -> None:
        client = get_clickhouse_ingest()
        client.insert(
            CH_MINUTE_TABLE,
            [[minute.replace(second=0, microsecond=0), int(requests), site_id]],
            column_names=["minute", "requests", "site_id"],
        )

    def insert_window_snapshots(
        self,
        ts: datetime,
        samples: list[WindowSample],
    ) -> None:
        if not samples:
            return
        self.ensure_schema()
        rows = [
            [
                ts.replace(second=0, microsecond=0),
                s.site_id,
                int(s.window_sec),
                int(s.requests),
                float(s.qps),
            ]
            for s in samples
        ]
        client = get_clickhouse_ingest()
        client.insert(
            CH_WINDOW_SNAPSHOT_TABLE,
            rows,
            column_names=["ts", "site_id", "window_sec", "requests", "qps"],
        )

    def current_window_requests(
        self,
        window_sec: int,
        *,
        site_id: int | None = None,
        as_of: datetime | None = None,
    ) -> int:
        """Sum minute rollups over the trailing analysis window."""
        as_of = (as_of or datetime.utcnow()).replace(second=0, microsecond=0)
        start = as_of - timedelta(seconds=window_sec)
        site_clause = (
            "site_id IS NULL"
            if site_id is None
            else "site_id = {site_id:UInt32}"
        )
        params: dict = {"start": start, "end": as_of}
        if site_id is not None:
            params["site_id"] = site_id
        client = get_clickhouse()
        row = client.query(
            f"""
            SELECT coalesce(sum(requests), 0) AS total
            FROM {CH_MINUTE_TABLE}
            WHERE {site_clause}
              AND minute > {{start:DateTime}}
              AND minute <= {{end:DateTime}}
            """,
            parameters=params,
        ).result_rows
        return int(row[0][0]) if row else 0

    def same_slot_window_averages(
        self,
        window_sec: int,
        *,
        site_id: int | None = None,
        lookback_days: int = 28,
        as_of_utc: datetime | None = None,
        timezone_name: str = "Asia/Shanghai",
        slot_mode: str = "quarter",
        outlier_quantile: float = 0.95,
    ) -> tuple[float, int]:
        """Median bucket totals for a historical traffic slot aligned to *as_of_utc*.

        Slot modes (most to least specific):
        - quarter: same weekday + hour + 15-minute quarter
        - hour: same weekday + hour
        - hour_only: same hour across all weekdays (warm-start fallback)

        Minute rollups in ClickHouse are UTC; slot alignment uses *timezone_name*.
        """
        as_of_utc = (as_of_utc or datetime.utcnow()).replace(second=0, microsecond=0)
        local_as_of = local_datetime(as_of_utc, timezone_name)
        bucket_expr = _bucket_expr(window_sec)
        site_clause = (
            "site_id IS NULL"
            if site_id is None
            else "site_id = {site_id:UInt32}"
        )
        local_minute = f"toTimeZone(minute, {{tz:String}})"
        slot_clause = _slot_filters(slot_mode, local_minute)
        params: dict = {
            "lookback_days": lookback_days,
            "dow": local_as_of.isoweekday(),
            "hour": local_as_of.hour,
            "quarter": local_as_of.minute // 15,
            "as_of": as_of_utc,
            "tz": timezone_name,
            "outlier_q": outlier_quantile,
        }
        if site_id is not None:
            params["site_id"] = site_id

        client = get_clickhouse()
        rows = client.query(
            f"""
            WITH buckets AS (
              SELECT {bucket_expr} AS bucket, sum(requests) AS total
              FROM {CH_MINUTE_TABLE}
              WHERE {site_clause}
                AND minute >= {{as_of:DateTime}} - INTERVAL {{lookback_days:UInt16}} DAY
                AND minute < {{as_of:DateTime}}
                {slot_clause}
              GROUP BY bucket
            ),
            filtered AS (
              SELECT total
              FROM buckets
              WHERE total > 0
                AND total <= (
                  SELECT quantile({{outlier_q:Float64}})(total)
                  FROM buckets
                  WHERE total > 0
                )
            )
            SELECT quantile(0.5)(total) AS avg_r, count() AS samples
            FROM filtered
            """,
            parameters=params,
        ).result_rows
        if not rows or rows[0][1] == 0:
            return 0.0, 0
        return float(rows[0][0]), int(rows[0][1])

    def recent_minute_series(
        self,
        *,
        site_id: int | None = None,
        hours: int = 24,
    ) -> list[dict]:
        site_clause = (
            "site_id IS NULL"
            if site_id is None
            else "site_id = {site_id:UInt32}"
        )
        params: dict = {"hours": hours}
        if site_id is not None:
            params["site_id"] = site_id
        client = get_clickhouse()
        rows = client.query(
            f"""
            SELECT minute, sum(requests) AS requests
            FROM {CH_MINUTE_TABLE}
            WHERE {site_clause}
              AND minute >= now() - INTERVAL {{hours:UInt16}} HOUR
            GROUP BY minute
            ORDER BY minute
            """,
            parameters=params,
        ).result_rows
        return [{"minute": r[0], "requests": int(r[1])} for r in rows]
