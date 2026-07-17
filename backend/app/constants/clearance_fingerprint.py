"""Clearance fingerprint dimension catalog (backend source of truth)."""

from __future__ import annotations

FINGERPRINT_DIMENSION_OPTIONS: list[dict[str, str | bool]] = [
    {
        "key": "ip",
        "label": "客户端 IP",
        "description": "访客 IP 地址（必选）",
        "required": True,
    },
    {
        "key": "ua",
        "label": "User-Agent",
        "description": "浏览器 UA",
        "required": False,
    },
    {
        "key": "accept_language",
        "label": "Accept-Language",
        "description": "语言偏好",
        "required": False,
    },
    {
        "key": "accept_encoding",
        "label": "Accept-Encoding",
        "description": "压缩编码",
        "required": False,
    },
    {
        "key": "sec_ch_ua",
        "label": "Sec-CH-UA",
        "description": "浏览器品牌/版本",
        "required": False,
    },
    {
        "key": "sec_ch_ua_platform",
        "label": "Sec-CH-UA-Platform",
        "description": "操作系统平台",
        "required": False,
    },
]

ALLOWED_FINGERPRINT_DIMS = frozenset(
    opt["key"] for opt in FINGERPRINT_DIMENSION_OPTIONS
)

DEFAULT_CLEARANCE_FINGERPRINT_DIMS: list[str] = ["ip", "ua"]
