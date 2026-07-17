"""Origin (upstream) parsing, validation and display helpers."""
from __future__ import annotations

import ipaddress
import re

_DOCKER_HOST_ALIASES = frozenset({"host.docker.internal", "localhost"})

_HOST_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$"
)


def normalize_origin_host(value: str) -> str:
    """Strip scheme and trailing port from user input."""
    value = value.strip()
    m = re.match(r"^https?://(.+)$", value, re.I)
    if m:
        value = m.group(1).strip()
    if value.startswith("["):
        m6 = re.match(r"^\[([^\]]+)\](?::(\d+))?$", value)
        if m6:
            return m6.group(1)
        return value.strip("[]")
    if ":" in value and value.count(":") == 1:
        host, port = value.rsplit(":", 1)
        if port.isdigit():
            return host
    return value


def validate_origin_host(value: str) -> str:
    value = normalize_origin_host(value)
    if not value:
        raise ValueError("请输入合法的域名或 IP")
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if value in {"localhost", "host.docker.internal"} or _HOST_RE.match(value):
        return value
    raise ValueError("请输入合法的域名或 IP")


def format_origin_display(
    host: str,
    protocol: str,
    http_port: int,
    https_port: int,
) -> str:
    if protocol == "follow":
        return f"{host}（跟随协议 · {http_port}/{https_port}）"
    if protocol == "http":
        return f"http://{host}:{http_port}"
    return f"https://{host}:{https_port}"


def resolve_origin_host_for_engine(host: str) -> str:
    """Resolve Docker host aliases to an IP for OpenResty variable upstream URLs.

    Nginx resolves variable ``proxy_pass`` targets via ``resolver`` (Docker DNS),
    which does not read ``/etc/hosts`` entries such as ``host.docker.internal``.
    """
    host = normalize_origin_host(host)
    if host in _DOCKER_HOST_ALIASES:
        from app.core.config import settings

        return settings.waf_origin_host_gateway
    return host


def build_upstream_url(host: str, protocol: str, port: int) -> str:
    host = resolve_origin_host_for_engine(host)
    return f"{protocol}://{host}:{port}"
