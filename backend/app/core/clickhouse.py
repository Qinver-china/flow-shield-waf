"""ClickHouse client factory.

Query paths use a fresh client per call (clickhouse-connect HTTP sessions are not
safe for concurrent use on the same object). Prefer ``clickhouse_client()`` so the
client is always closed after the query batch.

Log ingest uses a thread-local client with optional async_insert so worker threads
reuse connections without cross-thread sharing.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Iterator

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
    """Create a fresh query client. Prefer ``clickhouse_client()`` to ensure close()."""
    return clickhouse_connect.get_client(**_client_kwargs())


@contextmanager
def clickhouse_client() -> Iterator:
    """Fresh query client with guaranteed close (avoids FD/connection leaks)."""
    client = get_clickhouse()
    try:
        yield client
    finally:
        try:
            client.close()
        except Exception:  # noqa: BLE001
            pass


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
        with clickhouse_client() as client:
            client.command("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False
