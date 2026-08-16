from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _normalize_acme_provider(value: str | None) -> str | None:
    provider = (value or "").strip().lower()
    if not provider:
        return None
    if provider not in {"letsencrypt", "zerossl"}:
        raise ValueError("请选择 Let's Encrypt 或 ZeroSSL")
    return provider


def _normalize_renew_domains(domains: list[str] | None) -> list[str] | None:
    if domains is None:
        return None
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in domains:
        name = str(item or "").strip().lower().rstrip(".")
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


class CertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_content: str = Field(min_length=1)
    key_content: str = Field(min_length=1)
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    acme_auto_renew: bool = False
    acme_provider: str | None = None
    renew_domains: list[str] | None = None

    @model_validator(mode="after")
    def _validate_notify_and_renew(self) -> "CertificateCreate":
        needs_channels = self.expiry_notify_enabled or self.acme_auto_renew
        if needs_channels and not self.expiry_notify_channel_ids:
            if self.acme_auto_renew:
                raise ValueError("开启自动续期时请选择通知通道")
            raise ValueError("启用到期前通知时请选择通知通道")
        self.acme_provider = _normalize_acme_provider(self.acme_provider)
        self.renew_domains = _normalize_renew_domains(self.renew_domains)
        if self.acme_auto_renew:
            if not self.acme_provider:
                raise ValueError("开启自动续期时请选择证书机构")
            if not self.renew_domains:
                raise ValueError("开启自动续期时请选择绑定域名")
        return self


class CertificateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    cert_content: str | None = None
    key_content: str | None = None
    remark: str | None = None
    expiry_notify_enabled: bool | None = None
    expiry_notify_channel_ids: list[int] | None = None
    acme_auto_renew: bool | None = None
    acme_provider: str | None = None
    renew_domains: list[str] | None = None

    @model_validator(mode="after")
    def _normalize_acme_fields(self) -> "CertificateUpdate":
        if "acme_provider" in self.model_fields_set:
            self.acme_provider = _normalize_acme_provider(self.acme_provider)
        if "renew_domains" in self.model_fields_set:
            self.renew_domains = _normalize_renew_domains(self.renew_domains)
        return self


class AcmeIssueRequest(BaseModel):
    site_id: int
    domains: list[str] = Field(min_length=1)
    provider: str
    auto_renew: bool = False
    expiry_notify_enabled: bool = False
    expiry_notify_channel_ids: list[int] = Field(default_factory=list)
    renew_domains: list[str] | None = None
    name: str | None = Field(default=None, max_length=128)
    replace_certificate_id: int | None = None

    @model_validator(mode="after")
    def _validate_acme_issue(self) -> "AcmeIssueRequest":
        provider = (self.provider or "").strip().lower()
        if provider not in {"letsencrypt", "zerossl"}:
            raise ValueError("请选择 Let's Encrypt 或 ZeroSSL")
        self.provider = provider
        self.renew_domains = _normalize_renew_domains(self.renew_domains)
        needs_channels = self.auto_renew or self.expiry_notify_enabled
        if needs_channels and not self.expiry_notify_channel_ids:
            if self.auto_renew:
                raise ValueError("开启自动续期时请选择通知通道")
            raise ValueError("启用到期前通知时请选择通知通道")
        if self.auto_renew and self.renew_domains is not None and not self.renew_domains:
            raise ValueError("开启自动续期时请选择绑定域名")
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
