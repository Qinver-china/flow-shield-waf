"""Validate and normalize IP / CIDR entries for IP groups."""
from __future__ import annotations

import ipaddress
import re

_IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def _unwrap_ip_brackets(text: str) -> str:
    """Strip optional IPv6 brackets, keeping a trailing CIDR prefix.

    @param text: Raw IP or CIDR, possibly wrapped as ``[2001:db8::1]`` / ``[2001:db8::]/32``.
    @return: The same value without surrounding brackets.
    """
    if text.startswith("["):
        end = text.find("]")
        if end != -1:
            return text[1:end] + text[end + 1 :]
    return text


def normalize_entry(raw: str) -> str:
    """Normalize a single IPv4/IPv6 address or CIDR to canonical form.

    @param raw: User-supplied IP or CIDR (IPv6 may use brackets).
    @return: Compressed address or network string.
    """
    text = _unwrap_ip_brackets((raw or "").strip())
    if not text:
        raise ValueError("IP 条目不能为空")
    if "%" in text:
        raise ValueError(f"无效 IP 或网段: {text}")
    if "/" in text:
        try:
            net = ipaddress.ip_network(text, strict=False)
        except ValueError as exc:
            raise ValueError(f"无效网段: {text}") from exc
        return str(net)
    if _IPV4_RE.match(text):
        parts = [int(p) for p in text.split(".")]
        if any(p > 255 for p in parts):
            raise ValueError(f"无效 IP: {text}")
        return ".".join(str(p) for p in parts)
    try:
        ip = ipaddress.ip_address(text)
    except ValueError as exc:
        raise ValueError(f"无效 IP 或网段: {text}") from exc
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return str(mapped)
    return str(ip)


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
