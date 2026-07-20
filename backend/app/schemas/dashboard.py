from datetime import datetime

from pydantic import BaseModel, Field


class RuleSyncHealthOut(BaseModel):
    version: int | None = None
    last_published_at: datetime | None = None
    status: str = "ok"


class DashboardHealthOut(BaseModel):
    database: str
    redis: str
    clickhouse: str
    rule_sync: RuleSyncHealthOut


class DashboardFeedItemOut(BaseModel):
    id: str
    type: str
    title: str
    detail: str | None = None
    site: str | None = None
    rule: str | None = None
    severity: str = "info"
    created_at: datetime


class DashboardFeedOut(BaseModel):
    items: list[DashboardFeedItemOut]
    pending_ai_incidents: int = 0


class DashboardSummaryOut(BaseModel):
    blocked_delta_pct: float | None = None
    passed_delta_pct: float | None = None
    total_requests_delta_pct: float | None = None
    unique_ips_delta_pct: float | None = None
    current: dict = Field(default_factory=dict)
    previous: dict = Field(default_factory=dict)
