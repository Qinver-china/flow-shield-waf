from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BaselineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    site_id: int | None
    window_sec: int
    slot_key: str
    strategy: str
    avg_requests: float
    sample_count: int
    updated_at: datetime | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class WindowComparison(BaseModel):
    window_sec: int
    label: str
    current_requests: int
    baseline_avg: float | None = None
    baseline_sample_count: int | None = None
    baseline_warmup: bool = False
    deviation_ratio: float | None = None
    spike_threshold_ratio: float = 0.5
    is_anomaly: bool = False


class IntelStatusOut(BaseModel):
    site_id: int | None = None
    spike_ratio: float
    baseline_lookback_days: int
    windows: list[WindowComparison] = Field(default_factory=list)


class MinuteSeriesPoint(BaseModel):
    minute: datetime
    requests: int
