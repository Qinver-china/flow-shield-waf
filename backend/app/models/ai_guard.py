"""AI Guard module persistence models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

APPLY_MODES = ("suggest_only", "auto_observe", "auto_block")
INCIDENT_STATUSES = ("pending", "analyzing", "suggested", "applied", "failed", "dismissed")
MESSAGE_ROLES = ("user", "assistant", "system", "tool")


class AiGuardSetting(Base, TimestampMixin):
    """Singleton AI Guard configuration (id=1)."""

    __tablename__ = "ai_guard_setting"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    provider_base_url: Mapped[str] = mapped_column(String(512), default="https://api.openai.com/v1")
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String(128), default="gpt-4o-mini")
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)
    chat_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    defense_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_apply_mode: Mapped[str] = mapped_column(String(24), default="suggest_only")
    max_logs_per_analysis: Mapped[int] = mapped_column(Integer, default=200)
    analysis_cooldown_sec: Mapped[int] = mapped_column(Integer, default=300)
    auto_block_min_confidence: Mapped[float] = mapped_column(Float, default=0.85)


class AiGuardPolicy(Base, TimestampMixin):
    """Automated defense trigger policy."""

    __tablename__ = "ai_guard_policy"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_type: Mapped[str] = mapped_column(String(64), index=True)
    trigger_params: Mapped[dict] = mapped_column(JSON, default=dict)
    apply_mode: Mapped[str] = mapped_column(String(24), default="suggest_only")
    notify_on: Mapped[list] = mapped_column(JSON, default=list)
    channel_ids: Mapped[list] = mapped_column(JSON, default=list)
    condition_filter: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cooldown_sec: Mapped[int] = mapped_column(Integer, default=300)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AiGuardIncident(Base, TimestampMixin):
    """One defense analysis run and its outcome."""

    __tablename__ = "ai_guard_incident"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    policy_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    site_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    trigger_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    log_sample_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    suggested_rule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applied_rule_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    apply_mode: Mapped[str | None] = mapped_column(String(24), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    notification_log: Mapped[list | None] = mapped_column(JSON, nullable=True)


class AiGuardChatSession(Base, TimestampMixin):
    __tablename__ = "ai_guard_chat_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), default="新对话")
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)


class AiGuardChatMessage(Base, TimestampMixin):
    __tablename__ = "ai_guard_chat_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text, default="")
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    pending_action: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    action_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
