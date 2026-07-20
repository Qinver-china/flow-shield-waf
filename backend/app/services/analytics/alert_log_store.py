"""ClickHouse store for alert policy notification delivery logs."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.core.clickhouse import get_clickhouse, get_clickhouse_ingest
from app.services.analytics.constants import CH_ALERT_LOGS_TABLE
from app.services.analytics.ids import next_alert_log_id

log = logging.getLogger("waf.analytics.alert_logs")

_COLUMNS = ["id", "policy_id", "channel_id", "status", "message", "detail", "created_at"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class AlertNotificationLogRecord:
    id: int
    policy_id: int
    channel_id: int
    status: str
    message: str
    detail: str | None = None
    created_at: datetime | None = None


class AlertLogStore:
    async def insert(
        self,
        *,
        policy_id: int,
        channel_id: int,
        status: str,
        message: str,
        detail: str | None = None,
    ) -> AlertNotificationLogRecord:
        row_id = await next_alert_log_id()
        created_at = _utcnow()
        rec = AlertNotificationLogRecord(
            id=row_id,
            policy_id=policy_id,
            channel_id=channel_id,
            status=status,
            message=message,
            detail=detail,
            created_at=created_at,
        )
        await self._insert_rows([rec])
        return rec

    async def insert_many(self, entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        records: list[AlertNotificationLogRecord] = []
        now = _utcnow()
        for entry in entries:
            row_id = await next_alert_log_id()
            records.append(
                AlertNotificationLogRecord(
                    id=row_id,
                    policy_id=int(entry["policy_id"]),
                    channel_id=int(entry.get("channel_id", 0)),
                    status=str(entry.get("status", "sent")),
                    message=str(entry.get("message", "")),
                    detail=entry.get("detail"),
                    created_at=entry.get("created_at") or now,
                )
            )
        await self._insert_rows(records)

    async def list_recent(self, *, limit: int = 50) -> list[AlertNotificationLogRecord]:
        def _query():
            client = get_clickhouse()
            rows = client.query(
                f"""
                SELECT id, policy_id, channel_id, status, message, detail, created_at
                FROM {CH_ALERT_LOGS_TABLE}
                ORDER BY created_at DESC, id DESC
                LIMIT {{limit:UInt32}}
                """,
                parameters={"limit": int(limit)},
            ).result_rows
            return [
                AlertNotificationLogRecord(
                    id=int(r[0]),
                    policy_id=int(r[1]),
                    channel_id=int(r[2]),
                    status=str(r[3]),
                    message=str(r[4]),
                    detail=r[5],
                    created_at=r[6],
                )
                for r in rows
            ]

        return await asyncio.to_thread(_query)

    async def latest_status_by_policy(self, policy_ids: list[int]) -> dict[int, str]:
        if not policy_ids:
            return {}

        def _query():
            client = get_clickhouse()
            rows = client.query(
                f"""
                SELECT policy_id, argMax(status, created_at) AS status
                FROM {CH_ALERT_LOGS_TABLE}
                WHERE policy_id IN {{ids:Array(UInt32)}}
                GROUP BY policy_id
                """,
                parameters={"ids": [int(i) for i in policy_ids]},
            ).result_rows
            return {int(r[0]): str(r[1]) for r in rows}

        return await asyncio.to_thread(_query)

    async def _insert_rows(self, records: list[AlertNotificationLogRecord]) -> None:
        rows = [
            [
                rec.id,
                rec.policy_id,
                rec.channel_id,
                rec.status,
                rec.message,
                rec.detail,
                rec.created_at or _utcnow(),
            ]
            for rec in records
        ]

        def _write():
            get_clickhouse_ingest().insert(CH_ALERT_LOGS_TABLE, rows, column_names=_COLUMNS)

        await asyncio.to_thread(_write)
