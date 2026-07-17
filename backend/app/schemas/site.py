from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants.response_pages import (
    ALLOWED_BLOCK_STATUS_CODES,
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
    DEFAULT_CAPTCHA_FOOTER_HTML,
)
from app.services.origin import (
    ORIGIN_PROTOCOLS,
    format_origin_display,
    validate_origin_host,
)


class SiteBase(BaseModel):
    name: str
    domain: str
    origin_host: str
    origin_protocol: str = "follow"
    origin_http_port: int = Field(default=80, ge=1, le=65535)
    origin_https_port: int = Field(default=443, ge=1, le=65535)
    listen_http: bool = True
    listen_https: bool = False
    certificate_id: int | None = None
    enabled: bool = True
    custom_block_page_enabled: bool = False
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None
    custom_captcha_footer_enabled: bool = False
    captcha_footer_html: str | None = None

    @field_validator("block_page_status_code")
    @classmethod
    def _validate_block_status(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in ALLOWED_BLOCK_STATUS_CODES:
            allowed = ", ".join(str(code) for code in sorted(ALLOWED_BLOCK_STATUS_CODES))
            raise ValueError(f"不支持的响应状态码，可选：{allowed}")
        return value

    @model_validator(mode="after")
    def _validate_response_pages(self) -> "SiteBase":
        if self.custom_block_page_enabled:
            if self.block_page_status_code is None:
                self.block_page_status_code = DEFAULT_BLOCK_PAGE_STATUS
            if not (self.block_page_html or "").strip():
                self.block_page_html = DEFAULT_BLOCK_PAGE_HTML
        if self.custom_captcha_footer_enabled and not (self.captcha_footer_html or "").strip():
            self.captcha_footer_html = DEFAULT_CAPTCHA_FOOTER_HTML
        return self

    @field_validator("origin_host")
    @classmethod
    def _normalize_host(cls, v: str) -> str:
        return validate_origin_host(v)

    @field_validator("origin_protocol")
    @classmethod
    def _check_protocol(cls, v: str) -> str:
        if v not in ORIGIN_PROTOCOLS:
            raise ValueError("回源协议无效")
        return v

    @model_validator(mode="after")
    def _check_listen_and_certs(self) -> "SiteBase":
        if not self.listen_http and not self.listen_https:
            raise ValueError("至少需要开启 HTTP 或 HTTPS 监听")
        if self.listen_https and not self.certificate_id:
            raise ValueError("开启 HTTPS 时必须选择 SSL 证书")
        return self


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    origin_host: str | None = None
    origin_protocol: str | None = None
    origin_http_port: int | None = Field(default=None, ge=1, le=65535)
    origin_https_port: int | None = Field(default=None, ge=1, le=65535)
    listen_http: bool | None = None
    listen_https: bool | None = None
    certificate_id: int | None = None
    enabled: bool | None = None
    custom_block_page_enabled: bool | None = None
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None
    custom_captcha_footer_enabled: bool | None = None
    captcha_footer_html: str | None = None

    @field_validator("block_page_status_code")
    @classmethod
    def _validate_block_status(cls, value: int | None) -> int | None:
        if value is None:
            return value
        if value not in ALLOWED_BLOCK_STATUS_CODES:
            allowed = ", ".join(str(code) for code in sorted(ALLOWED_BLOCK_STATUS_CODES))
            raise ValueError(f"不支持的响应状态码，可选：{allowed}")
        return value

    @field_validator("origin_host")
    @classmethod
    def _normalize_host(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_origin_host(v)

    @field_validator("origin_protocol")
    @classmethod
    def _check_protocol(cls, v: str | None) -> str | None:
        if v is not None and v not in ORIGIN_PROTOCOLS:
            raise ValueError("回源协议无效")
        return v


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    certificate_name: str | None = None
    origin_display: str | None = None

    @classmethod
    def from_site(cls, site) -> "SiteOut":
        out = cls.model_validate(site)
        if site.certificate:
            out.certificate_name = site.certificate.name
        out.origin_display = format_origin_display(
            site.origin_host,
            site.origin_protocol,
            site.origin_http_port,
            site.origin_https_port,
        )
        return out


class SiteOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    domain: str
    enabled: bool
