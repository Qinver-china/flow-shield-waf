"""ClickHouse client factory.

Query paths use a fresh client per call (clickhouse-connect HTTP sessions are not
safe for concurrent use on the same object).

Log ingest uses a thread-local client with optional async_insert so worker threads
reuse connections without cross-thread sharing.
"""
from __future__ import annotations

import logging
import threading

import clickhouse_connect

from app.core.config import settings

log = logging.getLogger("waf.clickhouse")

_ingest_local = threading.local()


def _client_kwargs() -> dict:
    return {
        "host": settings.clickhouse_host,
        "port": settings.clickhouse_port,
        "username": settings.clickhouse_user,
        "password": settings.clickhouse_password,
        "database": settings.clickhouse_database,
    }


def _ingest_settings() -> dict[str, int]:
    if not settings.clickhouse_async_insert:
        return {}
    return {
        "async_insert": 1,
        "wait_for_async_insert": 1,
    }


def get_clickhouse():
    return clickhouse_connect.get_client(**_client_kwargs())


def get_clickhouse_ingest():
    """Thread-local client for sequential ingest workers (log collector, rollups)."""
    client = getattr(_ingest_local, "client", None)
    if client is None:
        ingest_settings = _ingest_settings()
        client = clickhouse_connect.get_client(
            **_client_kwargs(),
            settings=ingest_settings or None,
        )
        _ingest_local.client = client
    return client


def ping() -> bool:
    try:
        get_clickhouse().command("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False
