"""ClickHouse store for AI Guard defense incidents."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.clickhouse import get_clickhouse, get_clickhouse_ingest
from app.services.analytics.constants import CH_INCIDENTS_TABLE
from app.services.analytics.ids import next_incident_id

log = logging.getLogger("waf.analytics.incidents")

_COLUMNS = [
    "incident_id",
    "version",
    "policy_id",
    "site_id",
    "status",
    "trigger_snapshot",
    "log_sample_meta",
    "analysis_report",
    "suggested_rule",
    "applied_rule_id",
    "apply_mode",
    "error_detail",
    "notification_log",
    "created_at",
    "updated_at",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _json_str(value: Any) -> str:
    if value is None:
        return "{}"
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return "{}"


def _parse_json(raw: Any, default: Any) -> Any:
    if raw is None:
        return default
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default
    return default


@dataclass
class IncidentRecord:
    incident_id: int
    version: int
    policy_id: int | None
    site_id: int | None
    status: str
    trigger_snapshot: dict | None = None
    log_sample_meta: dict | None = None
    analysis_report: dict | None = None
    suggested_rule: dict | None = None
    applied_rule_id: int | None = None
    apply_mode: str | None = None
    error_detail: str | None = None
    notification_log: list | None = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def id(self) -> int:
        return self.incident_id


def _row_from_record(rec: IncidentRecord) -> list:
    return [
        int(rec.incident_id),
        int(rec.version),
        rec.policy_id,
        rec.site_id,
        rec.status or "",
        _json_str(rec.trigger_snapshot),
        _json_str(rec.log_sample_meta),
        _json_str(rec.analysis_report),
        _json_str(rec.suggested_rule),
        rec.applied_rule_id,
        rec.apply_mode,
        rec.error_detail,
        _json_str(rec.notification_log if rec.notification_log is not None else []),
        rec.created_at or _utcnow(),
        rec.updated_at or _utcnow(),
    ]


def _record_from_row(row: tuple) -> IncidentRecord:
    return IncidentRecord(
        incident_id=int(row[0]),
        version=int(row[1]),
        policy_id=int(row[2]) if row[2] is not None else None,
        site_id=int(row[3]) if row[3] is not None else None,
        status=str(row[4]),
        trigger_snapshot=_parse_json(row[5], None),
        log_sample_meta=_parse_json(row[6], None),
        analysis_report=_parse_json(row[7], None),
        suggested_rule=_parse_json(row[8], None),
        applied_rule_id=int(row[9]) if row[9] is not None else None,
        apply_mode=row[10],
        error_detail=row[11],
        notification_log=_parse_json(row[12], []),
        created_at=row[13],
        updated_at=row[14],
    )


_LATEST_JOIN = f"""
FROM {CH_INCIDENTS_TABLE} AS t
INNER JOIN (
  SELECT incident_id, max(version) AS max_version
  FROM {CH_INCIDENTS_TABLE}
  GROUP BY incident_id
) AS latest ON t.incident_id = latest.incident_id AND t.version = latest.max_version
"""


def _latest_select(where: str = "", order: str = "", limit: str = "") -> str:
    return f"""
SELECT
  t.incident_id,
  t.version,
  t.policy_id,
  t.site_id,
  t.status,
  t.trigger_snapshot,
  t.log_sample_meta,
  t.analysis_report,
  t.suggested_rule,
  t.applied_rule_id,
  t.apply_mode,
  t.error_detail,
  t.notification_log,
  t.created_at,
  t.updated_at
{_LATEST_JOIN}
{where}
{order}
{limit}
""".strip()


class IncidentStore:
    async def create(
        self,
        *,
        policy_id: int | None,
        site_id: int | None,
        status: str,
        trigger_snapshot: dict | None = None,
        apply_mode: str | None = None,
        notification_log: list | None = None,
    ) -> IncidentRecord:
        now = _utcnow()
        incident_id = await next_incident_id()
        rec = IncidentRecord(
            incident_id=incident_id,
            version=1,
            policy_id=policy_id,
            site_id=site_id,
            status=status,
            trigger_snapshot=trigger_snapshot,
            apply_mode=apply_mode,
            notification_log=notification_log or [],
            created_at=now,
            updated_at=now,
        )
        await self._insert(rec)
        return rec

    async def upsert(self, rec: IncidentRecord) -> IncidentRecord:
        latest = await self.get(rec.incident_id)
        now = _utcnow()
        if latest is None:
            if rec.created_at is None:
                rec.created_at = now
            if rec.version <= 0:
                rec.version = 1
        else:
            rec.version = latest.version + 1
            if rec.created_at is None:
                rec.created_at = latest.created_at
        rec.updated_at = now
        await self._insert(rec)
        return rec

    async def get(self, incident_id: int) -> IncidentRecord | None:
        def _query():
            client = get_clickhouse()
            rows = client.query(
                _latest_select(
                    where="WHERE t.incident_id = {id:UInt64}",
                    limit="LIMIT 1",
                ),
                parameters={"id": int(incident_id)},
            ).result_rows
            if not rows:
                return None
            return _record_from_row(rows[0])

        return await asyncio.to_thread(_query)

    async def list(
        self,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[IncidentRecord], int]:
        def _query():
            client = get_clickhouse()
            params: dict[str, Any] = {"offset": int(offset), "limit": int(limit)}
            where = ""
            if status:
                where = "WHERE t.status = {status:String}"
                params["status"] = status
            total_rows = client.query(
                f"SELECT count() {_LATEST_JOIN} {where}",
                parameters=params,
            ).result_rows
            total = int(total_rows[0][0]) if total_rows else 0
            rows = client.query(
                _latest_select(
                    where=where,
                    order="ORDER BY t.incident_id DESC",
                    limit="LIMIT {limit:UInt32} OFFSET {offset:UInt32}",
                ),
                parameters=params,
            ).result_rows
            return [_record_from_row(r) for r in rows], total

        return await asyncio.to_thread(_query)

    async def count_by_status(self, statuses: list[str]) -> int:
        if not statuses:
            return 0

        def _query():
            client = get_clickhouse()
            rows = client.query(
                f"""
                SELECT count()
                {_LATEST_JOIN}
                WHERE t.status IN {{statuses:Array(String)}}
                """,
                parameters={"statuses": list(statuses)},
            ).result_rows
            return int(rows[0][0]) if rows else 0

        return await asyncio.to_thread(_query)

    async def _insert(self, rec: IncidentRecord) -> None:
        row = _row_from_record(rec)

        def _write():
            get_clickhouse_ingest().insert(CH_INCIDENTS_TABLE, [row], column_names=_COLUMNS)

        await asyncio.to_thread(_write)
