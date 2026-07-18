from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    ts: datetime
    log_type: str
    source: str | None = None
    site_id: int | None = None
    domain: str | None = None
    client_ip: str | None = None
    geo_country: str | None = None
    method: str | None = None
    uri: str | None = None
    ua: str | None = None
    rule_id: int | None = None
    rule_name: str | None = None
    action: str | None = None
    mode: str | None = None
    blocked: bool = False
    request_id: str | None = None
    payload: dict | None = None


class LogQuery(BaseModel):
    start: datetime | None = None
    end: datetime | None = None
    log_type: str | None = None
    source: str | None = None
    site_id: int | None = None
    client_ip: str | None = None
    rule_id: int | None = None
    rule_name: str | None = None
    action: str | None = None
    mode: str | None = None
    blocked: bool | None = None
    domain: str | None = None
    geo_country: str | None = None
    geo_region: str | None = None
    geo_city: str | None = None
    geo_isp: str | None = None
    geo_ip_type: str | None = None
    geo_asn: int | None = None
    method: str | None = None
    scheme: str | None = None
    http_version: str | None = None
    uri_path: str | None = None
    uri_ext: str | None = None
    referer_host: str | None = None
    ip_is_private: bool | None = None
    xff_first: str | None = None
    ua: str | None = None
    ua_family: str | None = None
    ua_os: str | None = None
    ua_browser: str | None = None
    bot_name: str | None = None
    bot_category: str | None = None
    tls_version: str | None = None
    keyword: str | None = None
    filters: str | None = None
    page: int = 1
    page_size: int = 20


class LogStatsGroupItem(BaseModel):
    key: str
    label: str
    count: int


class LogStatsGroupOut(BaseModel):
    dimension: str
    start: datetime
    end: datetime
    total: int
    group_total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[LogStatsGroupItem]
