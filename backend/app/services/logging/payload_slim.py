"""Slim log payloads before ClickHouse storage — drop fields duplicated in top-level columns."""
from __future__ import annotations

_PROMOTED_HEADERS = frozenset({
    "user-agent",
    "referer",
    "cookie",
    "x-forwarded-for",
    "host",
})

_PAYLOAD_DROP_KEYS = frozenset({
    "evaluated",
    "request",
    "rule",
    "client_ip",
    "cookie_raw",
})


def slim_payload(payload: dict | None) -> dict:
    """Keep only non-column payload fields, stripping promoted HTTP headers."""
    if not isinstance(payload, dict):
        return {}

    out: dict = {}

    headers = payload.get("headers")
    if isinstance(headers, dict):
        slim_headers = {
            str(k): v
            for k, v in headers.items()
            if str(k).lower() not in _PROMOTED_HEADERS
        }
        if slim_headers:
            out["headers"] = slim_headers

    for key in ("cookies", "query"):
        val = payload.get(key)
        if isinstance(val, dict) and val:
            out[key] = val

    client = payload.get("client")
    if isinstance(client, dict):
        port = client.get("port")
        if port is not None:
            out["client"] = {"port": port}

    return out


def payload_for_storage(entry: dict) -> dict:
    """Normalize engine/legacy entries to the slim payload shape for persistence."""
    raw = entry.get("payload")
    if raw is None:
        raw = {
            k: entry[k]
            for k in ("client", "headers", "cookies", "query")
            if k in entry
        }
    elif isinstance(raw, dict):
        raw = {k: v for k, v in raw.items() if k not in _PAYLOAD_DROP_KEYS}
    else:
        return {}

    return slim_payload(raw if isinstance(raw, dict) else {})
