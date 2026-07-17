"""ClickHouse client factory.

clickhouse-connect HTTP sessions are not safe for concurrent queries. We return a
fresh client per call so async handlers and thread-pool workers never share state.
"""
from __future__ import annotations

import logging

import clickhouse_connect

from app.core.config import settings

log = logging.getLogger("waf.clickhouse")


def get_clickhouse():
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def ping() -> bool:
    try:
        get_clickhouse().command("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False
