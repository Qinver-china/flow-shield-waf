from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.display_settings import DEFAULT_TIMEZONE
from app.constants.engine_settings import (
    DEFAULT_MAX_UPLOAD_SIZE_MB,
    DEFAULT_ORIGIN_READ_TIMEOUT_SEC,
)
from app.constants.ratelimit_settings import DEFAULT_RATELIMIT_FAIL_OPEN
from app.models.base import Base, TimestampMixin


class WafSetting(Base, TimestampMixin):
    """Singleton global WAF settings (id=1)."""

    __tablename__ = "waf_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    js_challenge_ttl: Mapped[int] = mapped_column(Integer, default=1800)
    captcha_ttl: Mapped[int] = mapped_column(Integer, default=1800)
    clearance_fingerprint_dims: Mapped[str | None] = mapped_column(Text, nullable=True)

    logging_control_mode: Mapped[str] = mapped_column(String(24), default="manual")
    logging_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    logging_skip_observe: Mapped[bool] = mapped_column(Boolean, default=False)
    observe_sample_rate_idle: Mapped[float] = mapped_column(Float, default=1.0)
    observe_sample_rate_active: Mapped[float] = mapped_column(Float, default=1.0)
    logging_detail_on_block: Mapped[bool] = mapped_column(Boolean, default=True)
    logging_auto_thresholds: Mapped[str | None] = mapped_column(Text, nullable=True)
    logging_auto_cooldown_sec: Mapped[int] = mapped_column(Integer, default=120)
    logging_auto_observe_sample_rate: Mapped[float] = mapped_column(Float, default=1.0)
    log_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    debug_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    ratelimit_fail_open: Mapped[bool] = mapped_column(Boolean, default=DEFAULT_RATELIMIT_FAIL_OPEN)
    block_page_status_code: Mapped[int] = mapped_column(Integer, default=403)
    block_page_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    captcha_footer_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIMEZONE)
    panel_public_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    acme_account_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    max_upload_size_mb: Mapped[int] = mapped_column(Integer, default=DEFAULT_MAX_UPLOAD_SIZE_MB)
    origin_read_timeout_sec: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_ORIGIN_READ_TIMEOUT_SEC
    )
