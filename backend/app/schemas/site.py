from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants.response_pages import (
    ALLOWED_BLOCK_STATUS_CODES,
    DEFAULT_BLOCK_PAGE_HTML,
    DEFAULT_BLOCK_PAGE_STATUS,
    DEFAULT_CAPTCHA_FOOTER_HTML,
)
from app.constants.client_ip import CLIENT_IP_SOURCE_DEFAULT, CLIENT_IP_SOURCE_VALUES
from app.services.origin import (
    ORIGIN_PROTOCOLS,
    format_origin_display,
    validate_origin_host,
)
from app.services.site_domains import (
    format_domains_display,
    normalize_domain_list,
    site_domain_list,
)


def _coerce_domains_input(data: object) -> object:
    if not isinstance(data, dict):
        return data
    if data.get("domains") is None and data.get("domain"):
        data = {**data, "domains": [data["domain"]]}
    return data


class SiteBase(BaseModel):
    name: str
    domains: list[str] = Field(min_length=1)
    origin_host: str
    origin_protocol: str = "follow"
    origin_http_port: int = Field(default=80, ge=1, le=65535)
    origin_https_port: int = Field(default=443, ge=1, le=65535)
    client_ip_source: str = CLIENT_IP_SOURCE_DEFAULT
    listen_http: bool = True
    listen_https: bool = False
    force_https: bool = False
    disable_content_buffering: bool = False
    certificate_id: int | None = None
    enabled: bool = True
    custom_block_page_enabled: bool = False
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None
    custom_captcha_footer_enabled: bool = False
    captcha_footer_html: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_domain(cls, data: object) -> object:
        return _coerce_domains_input(data)

    @field_validator("domains", mode="before")
    @classmethod
    def _normalize_domains(cls, value: object) -> list[str]:
        if value is None:
            raise ValueError("至少输入一个域名")
        if isinstance(value, str):
            return normalize_domain_list(value)
        if isinstance(value, list):
            return normalize_domain_list(value)
        raise ValueError("域名格式无效")

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

    @field_validator("client_ip_source")
    @classmethod
    def _check_client_ip_source(cls, v: str) -> str:
        if v not in CLIENT_IP_SOURCE_VALUES:
            raise ValueError("客户端 IP 获取方式无效")
        return v

    @model_validator(mode="after")
    def _check_listen_and_certs(self) -> "SiteBase":
        if not self.listen_http and not self.listen_https:
            raise ValueError("至少需要开启 HTTP 或 HTTPS 监听")
        if self.listen_https and not self.certificate_id:
            raise ValueError("开启 HTTPS 时必须选择 SSL 证书")
        if self.force_https and not self.listen_https:
            raise ValueError("开启强制 HTTPS 需要先开启 HTTPS 监听")
        return self


class SiteCreate(SiteBase):
    pass


class SiteUpdate(BaseModel):
    name: str | None = None
    domains: list[str] | None = Field(default=None, min_length=1)
    origin_host: str | None = None
    origin_protocol: str | None = None
    origin_http_port: int | None = Field(default=None, ge=1, le=65535)
    origin_https_port: int | None = Field(default=None, ge=1, le=65535)
    client_ip_source: str | None = None
    listen_http: bool | None = None
    listen_https: bool | None = None
    force_https: bool | None = None
    disable_content_buffering: bool | None = None
    certificate_id: int | None = None
    enabled: bool | None = None
    custom_block_page_enabled: bool | None = None
    block_page_status_code: int | None = Field(default=None, ge=400, le=599)
    block_page_html: str | None = None
    custom_captcha_footer_enabled: bool | None = None
    captcha_footer_html: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_domain(cls, data: object) -> object:
        return _coerce_domains_input(data)

    @field_validator("domains", mode="before")
    @classmethod
    def _normalize_domains(cls, value: object) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return normalize_domain_list(value)
        if isinstance(value, list):
            return normalize_domain_list(value)
        raise ValueError("域名格式无效")

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

    @field_validator("client_ip_source")
    @classmethod
    def _check_client_ip_source(cls, v: str | None) -> str | None:
        if v is not None and v not in CLIENT_IP_SOURCE_VALUES:
            raise ValueError("客户端 IP 获取方式无效")
        return v


class SiteOut(SiteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    domain: str
    domains_display: str | None = None
    certificate_name: str | None = None
    origin_display: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_orm_site(cls, data: object) -> object:
        if hasattr(data, "domain"):
            domains = site_domain_list(data)
            return {
                "id": data.id,
                "name": data.name,
                "domain": data.domain,
                "domains": domains,
                "domains_display": format_domains_display(domains),
                "origin_host": data.origin_host,
                "origin_protocol": data.origin_protocol,
                "origin_http_port": data.origin_http_port,
                "origin_https_port": data.origin_https_port,
                "client_ip_source": getattr(data, "client_ip_source", CLIENT_IP_SOURCE_DEFAULT),
                "listen_http": data.listen_http,
                "listen_https": data.listen_https,
                "force_https": getattr(data, "force_https", False),
                "disable_content_buffering": getattr(data, "disable_content_buffering", False),
                "certificate_id": data.certificate_id,
                "enabled": data.enabled,
                "custom_block_page_enabled": data.custom_block_page_enabled,
                "block_page_status_code": data.block_page_status_code,
                "block_page_html": data.block_page_html,
                "custom_captcha_footer_enabled": data.custom_captcha_footer_enabled,
                "captcha_footer_html": data.captcha_footer_html,
                "certificate": getattr(data, "certificate", None),
            }
        return data

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
    domains: list[str]
    enabled: bool

    @model_validator(mode="before")
    @classmethod
    def _from_orm_site(cls, data: object) -> object:
        if hasattr(data, "domain"):
            domains = site_domain_list(data)
            return {
                "id": data.id,
                "name": data.name,
                "domain": data.domain,
                "domains": domains,
                "enabled": data.enabled,
            }
        return data
