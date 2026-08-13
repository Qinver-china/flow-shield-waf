"""Origin defaults when importing sites from an external panel."""
from __future__ import annotations

from urllib.parse import urlparse

SAME_SERVER_HTTP_ALT = 8080
SAME_SERVER_HTTPS_ALT = 4343
SKIP_SITE_NAMES = frozenset({"phpmyadmin", "0.default", "default"})


def remap_listen_ports(
    http_port: int | None,
    https_port: int | None,
    *,
    same_server: bool,
) -> tuple[int, int]:
    http_port = int(http_port or 80)
    https_port = int(https_port or 443)
    if not same_server:
        return http_port, https_port
    if http_port == 80:
        http_port = SAME_SERVER_HTTP_ALT
    elif http_port == 443:
        http_port = SAME_SERVER_HTTPS_ALT
    if https_port == 443:
        https_port = SAME_SERVER_HTTPS_ALT
    elif https_port == 80:
        https_port = SAME_SERVER_HTTP_ALT
    return http_port, https_port


def default_origin_host(panel_url: str, *, same_server: bool) -> str:
    if same_server:
        return "host.docker.internal"
    host = urlparse(panel_url).hostname
    return host or "host.docker.internal"


def should_skip_site_name(name: str) -> str | None:
    key = (name or "").strip().lower()
    if key in SKIP_SITE_NAMES:
        return f"跳过系统站点：{name}"
    return None
