"""Log type registry - the extensibility seam of the logging module.

New log types (e.g. a future "bot-score" log) only need to register here with
their type-specific payload fields; the collection, storage and query pipeline
stays unchanged.
"""
from __future__ import annotations

from enum import Enum


class LogType(str, Enum):
    PROTECTION = "protection"          # 防护日志
    ACCESS_CONTROL = "access-control"  # 访问控制日志
    AUDIT = "audit"                    # 系统/审计日志


# common queryable columns present on every log row
COMMON_FIELDS = [
    "ts", "log_type", "source", "site_id", "domain", "client_ip",
    "geo_country", "method", "uri", "ua", "rule_id", "rule_name",
    "action", "mode", "blocked", "request_id",
]

# registry: log_type -> extra payload fields (nested under log.payload)
_REGISTRY: dict[str, list[str]] = {
    LogType.PROTECTION.value: ["evaluated", "rule", "request", "client", "client_ip", "headers", "cookies", "cookie_raw", "query"],
    LogType.ACCESS_CONTROL.value: ["evaluated", "rule", "request", "client", "client_ip", "headers", "cookies", "cookie_raw", "query"],
    LogType.AUDIT.value: ["actor", "target", "changes"],
}


def register_log_type(log_type: str, payload_fields: list[str]) -> None:
    _REGISTRY[log_type] = payload_fields


def known_types() -> list[str]:
    return list(_REGISTRY.keys())


def payload_fields(log_type: str) -> list[str]:
    return _REGISTRY.get(log_type, [])
