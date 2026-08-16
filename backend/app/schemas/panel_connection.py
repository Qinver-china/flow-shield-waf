from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

PanelProvider = Literal["baota", "onepanel"]

PROVIDERS: frozenset[str] = frozenset({"baota", "onepanel"})
API_KEY_MASK = "******"


def normalize_panel_url(value: str) -> str:
    raw = (value or "").strip().rstrip("/")
    if not raw:
        raise ValueError("请填写面板地址")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("面板地址必须以 http:// 或 https:// 开头")
    if not parsed.netloc:
        raise ValueError("面板地址无效")
    return raw


class PanelConnectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider: PanelProvider
    panel_url: str = Field(min_length=8, max_length=512)
    same_server: bool = False
    verify_tls: bool = False
    enabled: bool = True
    remark: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        name = v.strip()
        if not name:
            raise ValueError("请填写名称")
        return name

    @field_validator("panel_url")
    @classmethod
    def _check_url(cls, v: str) -> str:
        return normalize_panel_url(v)


class PanelConnectionCreate(PanelConnectionBase):
    api_key: str = ""


class PanelConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    panel_url: str | None = None
    api_key: str | None = None
    same_server: bool | None = None
    verify_tls: bool | None = None
    enabled: bool | None = None
    remark: str | None = None
    extra: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        name = v.strip()
        if not name:
            raise ValueError("请填写名称")
        return name

    @field_validator("panel_url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_panel_url(v)


class PanelConnectionOut(PanelConnectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    has_api_key: bool = False
    api_key_masked: str | None = None


class PanelConnectionTestBody(BaseModel):
    """Optional unsaved credentials for testing before create."""

    provider: PanelProvider | None = None
    panel_url: str | None = None
    api_key: str | None = None
    verify_tls: bool | None = None
    extra: dict[str, Any] | None = None

    @field_validator("panel_url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return normalize_panel_url(v)


class PanelSitePreview(BaseModel):
    key: str
    name: str
    domains: list[str] = Field(default_factory=list)
    origin_http_port: int
    origin_https_port: int
    has_ssl: bool = False
    ssl_not_after: str | None = None
    force_https: bool = False
    already_imported: bool = False
    skip_reason: str | None = None


class PanelCertPreview(BaseModel):
    key: str
    name: str
    domains: list[str] = Field(default_factory=list)
    not_after: str | None = None
    already_imported: bool = False
    skip_reason: str | None = None


class PanelImportKeys(BaseModel):
    keys: list[str] = Field(min_length=1)
    origin_host: str | None = None
    origin_http_port: int | None = Field(default=None, ge=1, le=65535)
    origin_https_port: int | None = Field(default=None, ge=1, le=65535)
    replace_certificate_id: int | None = None


class PanelImportItemResult(BaseModel):
    key: str
    name: str | None = None
    status: Literal["imported", "skipped", "failed"]
    reason: str | None = None
    site_id: int | None = None
    certificate_id: int | None = None


class PanelImportResult(BaseModel):
    imported: list[PanelImportItemResult] = Field(default_factory=list)
    skipped: list[PanelImportItemResult] = Field(default_factory=list)
    failed: list[PanelImportItemResult] = Field(default_factory=list)
    warning: str | None = None
