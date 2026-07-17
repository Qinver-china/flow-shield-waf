"""Origin (upstream) parsing, validation and display helpers."""
from __future__ import annotations

import ipaddress
import re

ORIGIN_PROTOCOLS = frozenset({"follow", "http", "https"})

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


def build_upstream_url(host: str, protocol: str, port: int) -> str:
    return f"{protocol}://{host}:{port}"
