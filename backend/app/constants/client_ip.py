"""Per-site client IP resolution modes (CDN / reverse-proxy)."""

from __future__ import annotations

CLIENT_IP_SOURCE_DEFAULT = "remote_addr"

# value -> display label
CLIENT_IP_SOURCES: dict[str, str] = {
    "remote_addr": "直连 IP（TCP 连接地址）",
    "xff_first": "X-Forwarded-For（第一个 IP）",
    "xff_last": "X-Forwarded-For（最后一个 IP）",
    "x_real_ip": "X-Real-IP",
    "cf_connecting_ip": "CF-Connecting-IP（Cloudflare）",
    "true_client_ip": "True-Client-IP（Akamai 等）",
    "x_client_ip": "X-Client-IP",
}

CLIENT_IP_SOURCE_VALUES = frozenset(CLIENT_IP_SOURCES)

# Nginx realip module header mapping (xff modes use Lua only).
REAL_IP_HEADER_BY_SOURCE: dict[str, str] = {
    "x_real_ip": "X-Real-IP",
    "cf_connecting_ip": "CF-Connecting-IP",
    "true_client_ip": "True-Client-IP",
    "x_client_ip": "X-Client-IP",
}
