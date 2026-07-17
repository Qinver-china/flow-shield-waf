"""Validate and normalize IP / CIDR entries for IP groups."""
from __future__ import annotations

import ipaddress
import re

_IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def normalize_entry(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise ValueError("IP 条目不能为空")
    if "/" in text:
        try:
            net = ipaddress.ip_network(text, strict=False)
        except ValueError as exc:
            raise ValueError(f"无效网段: {text}") from exc
        if net.version != 4:
            raise ValueError(f"仅支持 IPv4 网段: {text}")
        return str(net)
    if _IPV4_RE.match(text):
        parts = [int(p) for p in text.split(".")]
        if any(p > 255 for p in parts):
            raise ValueError(f"无效 IP: {text}")
        return ".".join(str(p) for p in parts)
    raise ValueError(f"无效 IP 或网段: {text}")


def parse_lines(text: str) -> list[str]:
    if not text:
        return []
    lines = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        item = line.strip()
        if item and not item.startswith("#"):
            lines.append(item)
    return lines


def normalize_entries(raw_entries: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in raw_entries:
        entry = normalize_entry(raw)
        if entry not in seen:
            seen.add(entry)
            out.append(entry)
    return out
