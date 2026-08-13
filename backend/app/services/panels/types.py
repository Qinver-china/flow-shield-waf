from __future__ import annotations

from dataclasses import dataclass, field


class PanelError(Exception):
    """User-facing error talking to an external panel."""


@dataclass
class RawPanelSite:
    key: str
    name: str
    domains: list[str]
    http_port: int | None = None
    https_port: int | None = None
    has_ssl: bool = False
    ssl_not_after: str | None = None
    force_https: bool = False
    skip_reason: str | None = None


@dataclass
class RawPanelCert:
    key: str
    name: str
    domains: list[str] = field(default_factory=list)
    not_after: str | None = None
    skip_reason: str | None = None


@dataclass
class PemPair:
    cert_pem: str
    key_pem: str
    name: str
