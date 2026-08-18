"""Pydantic schemas for AI Guard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.ai_guard.mode_guide import APPLY_MODE_ALIASES, normalize_apply_mode

ApplyMode = Literal["suggest_only", "auto_observe", "auto_handle", "auto_block"]


def _norm_apply_mode(value: object) -> object:
    if value is None or value == "":
        return value
    return normalize_apply_mode(str(value))


def _alias_apply_mode_only(value: object) -> object:
    """Map legacy auto_block without rewriting engine action modes (observe/block/...)."""
    if value is None or value == "":
        return value
    raw = str(value).strip()
    return APPLY_MODE_ALIASES.get(raw, raw)


class AiGuardSettingOut(BaseModel):
    enabled: bool = False
    provider_base_url: str = "https://api.openai.com/v1"
    api_key_set: bool = False
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4096
    chat_enabled: bool = True
    floating_chat_enabled: bool = True
    defense_enabled: bool = True
    defense_web_search_enabled: bool = False
    default_apply_mode: ApplyMode = "auto_handle"
    max_logs_per_analysis: int = 200
    analysis_cooldown_sec: int = 300
    auto_block_min_confidence: float = 0.85

    @field_validator("default_apply_mode", mode="before")
    @classmethod
    def _coerce_default_apply_mode(cls, value: object) -> object:
        return _norm_apply_mode(value) or "auto_handle"


class AiGuardSettingUpdate(BaseModel):
    enabled: bool | None = None
    provider_base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=256, le=128000)
    chat_enabled: bool | None = None
    floating_chat_enabled: bool | None = None
    defense_enabled: bool | None = None
    defense_web_search_enabled: bool | None = None
    default_apply_mode: ApplyMode | None = None
    max_logs_per_analysis: int | None = Field(default=None, ge=10, le=2000)
    analysis_cooldown_sec: int | None = Field(default=None, ge=30, le=86400)
    auto_block_min_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("default_apply_mode", mode="before")
    @classmethod
    def _coerce_default_apply_mode(cls, value: object) -> object:
        return _norm_apply_mode(value)


class AiGuardPolicyBase(BaseModel):
    name: str
    enabled: bool = True
    trigger_type: str
    trigger_params: dict[str, Any] = Field(default_factory=dict)
    apply_mode: ApplyMode = "auto_handle"
    notify_on: list[str] = Field(default_factory=lambda: ["trigger", "result"])
    channel_ids: list[int] = Field(default_factory=list)
    condition_filter: dict[str, Any] | None = None
    cooldown_sec: int = 300
    remark: str | None = None
    custom_prompt: str | None = Field(default=None, max_length=4000)

    @field_validator("apply_mode", mode="before")
    @classmethod
    def _coerce_apply_mode(cls, value: object) -> object:
        return _norm_apply_mode(value) or "auto_handle"


class AiGuardPolicyCreate(AiGuardPolicyBase):
    pass


class AiGuardPolicyUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    trigger_type: str | None = None
    trigger_params: dict[str, Any] | None = None
    apply_mode: ApplyMode | None = None
    notify_on: list[str] | None = None
    channel_ids: list[int] | None = None
    condition_filter: dict[str, Any] | None = None
    cooldown_sec: int | None = None
    remark: str | None = None
    custom_prompt: str | None = Field(default=None, max_length=4000)

    @field_validator("apply_mode", mode="before")
    @classmethod
    def _coerce_apply_mode(cls, value: object) -> object:
        return _norm_apply_mode(value)


class AiGuardPolicyOut(AiGuardPolicyBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    last_triggered_at: datetime | None = None


class AiGuardIncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    policy_id: int | None
    site_id: int | None
    status: str
    trigger_snapshot: dict | None
    log_sample_meta: dict | None
    analysis_report: dict | None
    suggested_rule: dict | None
    applied_rule_id: int | None
    applied_rule_exists: bool = False
    apply_mode: str | None
    error_detail: str | None
    created_at: datetime | None

    @field_validator("apply_mode", mode="before")
    @classmethod
    def _coerce_apply_mode(cls, value: object) -> object:
        return _alias_apply_mode_only(value)


class ChatRequest(BaseModel):
    session_id: int | None = None
    message: str = Field(min_length=1, max_length=8000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    tool_calls: list | None = None
    pending_action: dict | None = None
    action_status: str | None = None
    created_at: datetime | None


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    created_at: datetime | None


class ConfirmActionRequest(BaseModel):
    message_id: int
    approved: bool = True
    edited_payload: dict[str, Any] | None = None


class ApplyIncidentRequest(BaseModel):
    apply_mode: ApplyMode | None = None

    @field_validator("apply_mode", mode="before")
    @classmethod
    def _coerce_apply_mode(cls, value: object) -> object:
        return _norm_apply_mode(value)
