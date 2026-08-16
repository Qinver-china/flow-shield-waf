from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_content: str = Field(min_length=1)
    key_content: str = Field(min_length=1)
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_channel_when_enabled(self) -> "CertificateCreate":
        if self.expiry_notify_enabled and not self.expiry_notify_channel_ids:
            raise ValueError("启用到期前通知时请选择通知通道")
        return self


class CertificateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    cert_content: str | None = None
    key_content: str | None = None
    remark: str | None = None
    expiry_notify_enabled: bool | None = None
    expiry_notify_channel_ids: list[int] | None = None
    acme_auto_renew: bool | None = None


class AcmeIssueRequest(BaseModel):
    site_id: int
    domains: list[str] = Field(min_length=1)
    provider: str
    auto_renew: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    name: str | None = Field(default=None, max_length=128)
    replace_certificate_id: int | None = None

    @model_validator(mode="after")
    def _require_channel_when_auto_renew(self) -> "AcmeIssueRequest":
        provider = (self.provider or "").strip().lower()
        if provider not in {"letsencrypt", "zerossl"}:
            raise ValueError("请选择 Let's Encrypt 或 ZeroSSL")
        self.provider = provider
        if self.auto_renew and not self.expiry_notify_channel_ids:
            raise ValueError("开启自动更新时请选择通知通道")
        return self


class CertificateBoundSite(BaseModel):
    id: int
    name: str


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domains: str | None = None
    cert_path: str
    key_path: str
    not_before: datetime | None = None
    not_after: datetime | None = None
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    acme_provider: str | None = None
    acme_auto_renew: bool = False
    acme_last_attempt_on: str | None = None
    acme_last_error: str | None = None
    bound_sites: list[CertificateBoundSite] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("expiry_notify_channel_ids", mode="before")
    @classmethod
    def _coerce_channel_ids(cls, value: object) -> list:
        return list(value or [])

    @field_validator("bound_sites", mode="before")
    @classmethod
    def _coerce_bound_sites(cls, value: object) -> list:
        return list(value or [])


class CertificateDetail(CertificateOut):
    cert_content: str = ""
    key_content: str = ""


class CertificateOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domains: str | None = None
    not_after: datetime | None = None
