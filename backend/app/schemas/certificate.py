from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_content: str = Field(min_length=1)
    key_content: str = Field(min_length=1)
    remark: str | None = None
    expiry_notify_enabled: bool = False
    expiry_notify_channel_id: int | None = None

    @model_validator(mode="after")
    def _require_channel_when_enabled(self) -> "CertificateCreate":
        if self.expiry_notify_enabled and not self.expiry_notify_channel_id:
            raise ValueError("启用到期前通知时请选择通知通道")
        return self


class CertificateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    cert_content: str | None = None
    key_content: str | None = None
    remark: str | None = None
    expiry_notify_enabled: bool | None = None
    expiry_notify_channel_id: int | None = None


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
    expiry_notify_channel_id: int | None = None
    created_at: datetime
    updated_at: datetime


class CertificateDetail(CertificateOut):
    cert_content: str = ""
    key_content: str = ""


class CertificateOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domains: str | None = None
    not_after: datetime | None = None
