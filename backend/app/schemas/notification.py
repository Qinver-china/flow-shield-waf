from datetime import datetime
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.alert_conditions import CHANNEL_TYPES, CONDITION_TYPE_MAP

EmailSecurity = Literal["ssl", "starttls", "plain"]


class EmailChannelConfig(BaseModel):
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(ge=1, le=65535, default=465)
    smtp_security: EmailSecurity = "ssl"
    smtp_user: str = ""
    smtp_password: str = ""
    from_address: str = Field(min_length=3)
    from_name: str = "流盾WAF"
    to_addresses: list[str] = Field(min_length=1)

    @field_validator("to_addresses")
    @classmethod
    def _non_empty_recipients(cls, v: list[str]) -> list[str]:
        email_re = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in v:
            item = (raw or "").strip()
            if not item or not email_re.match(item):
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(item)
        if not cleaned:
            raise ValueError("至少填写一个有效收件人邮箱")
        return cleaned


class NotificationChannelBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    channel_type: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None

    @field_validator("channel_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        allowed = {c["value"] for c in CHANNEL_TYPES}
        if v not in allowed:
            raise ValueError(f"不支持的通道类型: {v}")
        return v


class NotificationChannelCreate(NotificationChannelBase):
    pass


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    enabled: bool | None = None
    config: dict[str, Any] | None = None
    remark: str | None = None


class NotificationChannelOut(NotificationChannelBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    config_masked: dict[str, Any] | None = None


class AlertPolicyBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    enabled: bool = True
    condition_type: str
    condition_params: dict[str, Any] = Field(default_factory=dict)
    channel_ids: list[int] = Field(default_factory=list)
    cooldown_sec: int = Field(default=300, ge=60, le=86400)
    remark: str | None = None

    @field_validator("condition_type")
    @classmethod
    def _check_condition(cls, v: str) -> str:
        if v not in CONDITION_TYPE_MAP:
            raise ValueError(f"不支持的预警条件: {v}")
        return v


class AlertPolicyCreate(AlertPolicyBase):
    pass


class AlertPolicyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    enabled: bool | None = None
    condition_type: str | None = None
    condition_params: dict[str, Any] | None = None
    channel_ids: list[int] | None = None
    cooldown_sec: int | None = Field(default=None, ge=60, le=86400)
    remark: str | None = None


class AlertPolicyOut(AlertPolicyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    last_fired_at: datetime | None = None
    last_dispatch_status: str | None = None


class AlertNotificationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_id: int
    channel_id: int
    status: str
    message: str
    detail: str | None
    created_at: datetime | None
