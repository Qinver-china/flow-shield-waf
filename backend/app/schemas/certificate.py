from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CertificateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    cert_content: str = Field(min_length=1)
    key_content: str = Field(min_length=1)
    remark: str | None = None


class CertificateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    cert_content: str | None = None
    key_content: str | None = None
    remark: str | None = None


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
