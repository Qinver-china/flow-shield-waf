from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.logging_settings import (
    DEFAULT_AUTO_THRESHOLDS,
    DEFAULT_LOGGING_AUTO_COOLDOWN_SEC,
    DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE,
    DEFAULT_LOGGING_CONTROL_MODE,
    DEFAULT_LOGGING_DETAIL_ON_BLOCK,
    DEFAULT_LOGGING_ENABLED,
    DEFAULT_LOGGING_SKIP_OBSERVE,
    DEFAULT_LOG_RETENTION_DAYS,
    DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE,
    DEFAULT_OBSERVE_SAMPLE_RATE_IDLE,
    TRAFFIC_WINDOWS,
)
from app.services.waf_settings import normalize_auto_thresholds


class AutoThreshold(BaseModel):
    window_sec: int = Field(ge=1, le=86400)
    max_requests: int = Field(ge=1)


class LoggingSettings(BaseModel):
    logging_control_mode: str = Field(default=DEFAULT_LOGGING_CONTROL_MODE)
    logging_enabled: bool = DEFAULT_LOGGING_ENABLED
    logging_skip_observe: bool = DEFAULT_LOGGING_SKIP_OBSERVE
    observe_sample_rate_idle: float = Field(default=DEFAULT_OBSERVE_SAMPLE_RATE_IDLE, ge=0, le=1)
    observe_sample_rate_active: float = Field(
        default=DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE, ge=0, le=1
    )
    logging_detail_on_block: bool = DEFAULT_LOGGING_DETAIL_ON_BLOCK
    logging_auto_thresholds: list[AutoThreshold] = Field(
        default_factory=lambda: [AutoThreshold.model_validate(t) for t in DEFAULT_AUTO_THRESHOLDS]
    )
    logging_auto_cooldown_sec: int = Field(
        default=DEFAULT_LOGGING_AUTO_COOLDOWN_SEC, ge=10, le=3600
    )
    logging_auto_observe_sample_rate: float = Field(
        default=DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE, ge=0, le=1
    )
    log_retention_days: int = Field(default=DEFAULT_LOG_RETENTION_DAYS, ge=1, le=365)

    @field_validator("logging_control_mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        if value not in ("manual", "auto_by_traffic"):
            raise ValueError("logging_control_mode 只能是 manual 或 auto_by_traffic")
        return value

    @field_validator("logging_auto_thresholds")
    @classmethod
    def _validate_thresholds(cls, value: list[AutoThreshold]) -> list[AutoThreshold]:
        if not value:
            raise ValueError("至少配置一个流量阈值窗口")
        seen = {t.window_sec for t in value}
        if len(seen) != len(value):
            raise ValueError("流量阈值窗口不能重复")
        return value


class LoggingSettingsOut(LoggingSettings):
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_row(cls, row) -> "LoggingSettingsOut":
        thresholds = normalize_auto_thresholds(getattr(row, "logging_auto_thresholds", None))
        return cls(
            logging_control_mode=getattr(row, "logging_control_mode", None)
            or DEFAULT_LOGGING_CONTROL_MODE,
            logging_enabled=bool(getattr(row, "logging_enabled", DEFAULT_LOGGING_ENABLED)),
            logging_skip_observe=bool(
                getattr(row, "logging_skip_observe", DEFAULT_LOGGING_SKIP_OBSERVE)
            ),
            observe_sample_rate_idle=float(
                getattr(row, "observe_sample_rate_idle", DEFAULT_OBSERVE_SAMPLE_RATE_IDLE)
            ),
            observe_sample_rate_active=float(
                getattr(row, "observe_sample_rate_active", DEFAULT_OBSERVE_SAMPLE_RATE_ACTIVE)
            ),
            logging_detail_on_block=bool(
                getattr(row, "logging_detail_on_block", DEFAULT_LOGGING_DETAIL_ON_BLOCK)
            ),
            logging_auto_thresholds=[
                AutoThreshold.model_validate(t) for t in thresholds
            ],
            logging_auto_cooldown_sec=int(
                getattr(row, "logging_auto_cooldown_sec", DEFAULT_LOGGING_AUTO_COOLDOWN_SEC)
            ),
            logging_auto_observe_sample_rate=float(
                getattr(
                    row,
                    "logging_auto_observe_sample_rate",
                    DEFAULT_LOGGING_AUTO_OBSERVE_SAMPLE_RATE,
                )
            ),
            log_retention_days=int(
                getattr(row, "log_retention_days", DEFAULT_LOG_RETENTION_DAYS)
            ),
        )


def traffic_window_options() -> list[dict]:
    labels = {10: "10 秒", 30: "30 秒", 60: "1 分钟", 300: "5 分钟", 1800: "30 分钟", 3600: "60 分钟"}
    return [{"window_sec": w, "label": labels.get(w, f"{w} 秒")} for w in TRAFFIC_WINDOWS]
