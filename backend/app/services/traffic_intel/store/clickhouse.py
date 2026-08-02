"""ClickHouse persistence for traffic rollups and historical queries."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from app.core.clickhouse import get_clickhouse, get_clickhouse_ingest
from app.services.traffic_intel.constants import (
    CH_MINUTE_TABLE,
    CH_WINDOW_SNAPSHOT_TABLE,
    TRAFFIC_HISTORY_TTL_DAYS,
)
from app.services.traffic_intel.timezone import local_datetime
from app.services.traffic_intel.types import WindowSample

log = logging.getLogger("waf.traffic_intel.ch")
_ttl_synced = False


def _slot_filters(slot_mode: str, local_ts: str) -> str:
    """Time-of-day filters only (no weekday) for lightweight daily alignment."""
    if slot_mode == "quarter":
        return (
            f"AND toHour({local_ts}) = {{hour:UInt8}} "
            f"AND intDiv(toMinute({local_ts}), 15) = {{quarter:UInt8}}"
        )
    if slot_mode in ("hour", "hour_only"):
        return f"AND toHour({local_ts}) = {{hour:UInt8}}"
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
        ttl_days = int(TRAFFIC_HISTORY_TTL_DAYS)
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
            TTL ts + INTERVAL {ttl_days} DAY
            SETTINGS allow_nullable_key = 1
            """
        )
        # Existing installs keep CREATE IF NOT EXISTS; sync TTL once per process.
        global _ttl_synced
        if not _ttl_synced:
            for table, col in (
                (CH_WINDOW_SNAPSHOT_TABLE, "ts"),
                (CH_MINUTE_TABLE, "minute"),
            ):
                try:
                    client.command(
                        f"ALTER TABLE {table} MODIFY TTL {col} + INTERVAL {ttl_days} DAY"
                    )
                except Exception:  # noqa: BLE001
                    log.exception("failed to apply traffic TTL on %s", table)
            _ttl_synced = True

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
        """Median of historical *window snapshot* readings in an aligned slot.

        Uses ``traffic_window_snapshot`` (actual 1m/5m/30m/60m sliding totals at
        ingest time) instead of re-aggregating minute rollups. That keeps window
        baselines comparable to the live counters on the dashboard.

        Lightweight slot modes (time-of-day only, no weekday):
        - quarter: same hour + 15-minute quarter (every day)
        - hour / hour_only: same hour (every day)
        """
        as_of_utc = (as_of_utc or datetime.utcnow()).replace(second=0, microsecond=0)
        local_as_of = local_datetime(as_of_utc, timezone_name)
        site_clause = (
            "site_id IS NULL"
            if site_id is None
            else "site_id = {site_id:UInt32}"
        )
        local_ts = "toTimeZone(ts, {tz:String})"
        slot_clause = _slot_filters(slot_mode, local_ts)
        params: dict = {
            "lookback_days": lookback_days,
            "hour": local_as_of.hour,
            "quarter": local_as_of.minute // 15,
            "as_of": as_of_utc,
            "tz": timezone_name,
            "window_sec": int(window_sec),
            "outlier_q": outlier_quantile,
        }
        if site_id is not None:
            params["site_id"] = site_id

        client = get_clickhouse()
        # Prefer true window snapshots; fall back to minute-bucket reconstruction
        # only when the snapshot table is still empty (fresh installs).
        rows = client.query(
            f"""
            WITH raw AS (
              SELECT requests AS total
              FROM {CH_WINDOW_SNAPSHOT_TABLE}
              WHERE {site_clause}
                AND window_sec = {{window_sec:UInt32}}
                AND ts >= {{as_of:DateTime}} - INTERVAL {{lookback_days:UInt16}} DAY
                AND ts < {{as_of:DateTime}}
                AND requests > 0
                {slot_clause}
            ),
            bounds AS (
              SELECT count() AS n, quantile({{outlier_q:Float64}})(total) AS hi
              FROM raw
            ),
            filtered AS (
              SELECT r.total AS total
              FROM raw AS r
              CROSS JOIN bounds AS b
              WHERE b.n < 8 OR r.total <= b.hi
            )
            SELECT quantile(0.5)(total) AS avg_r, count() AS samples
            FROM filtered
            """,
            parameters=params,
        ).result_rows
        if rows and rows[0][1] and int(rows[0][1]) > 0:
            return float(rows[0][0]), int(rows[0][1])

        # Legacy fallback: reconstruct from minute rollups (may under-count long
        # windows when filtered by a finer slot than the bucket size).
        bucket_expr = _bucket_expr(window_sec)
        local_minute = "toTimeZone(minute, {tz:String})"
        minute_slot = _slot_filters(slot_mode, local_minute)
        rows = client.query(
            f"""
            WITH buckets AS (
              SELECT {bucket_expr} AS bucket, sum(requests) AS total
              FROM {CH_MINUTE_TABLE}
              WHERE {site_clause}
                AND minute >= {{as_of:DateTime}} - INTERVAL {{lookback_days:UInt16}} DAY
                AND minute < {{as_of:DateTime}}
                {minute_slot}
              GROUP BY bucket
            ),
            filtered AS (
              SELECT total
              FROM buckets
              WHERE total > 0
            )
            SELECT quantile(0.5)(total) AS avg_r, count() AS samples
            FROM filtered
            """,
            parameters=params,
        ).result_rows
        if not rows or rows[0][1] == 0:
            return 0.0, 0
        return float(rows[0][0]), int(rows[0][1])
