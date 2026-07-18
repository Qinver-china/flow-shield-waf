"""Consume Redis log stream and persist to ClickHouse."""
from __future__ import annotations

import asyncio
import json
import logging
import time

from app.core.config import settings
from app.core.redis import get_redis
from app.services.logging.bot_catalog_snapshot import refresh_from_redis
from app.services.logging.clickhouse_store import ClickHouseLogStore

log = logging.getLogger("waf.log_collector")

STREAM_KEY = "waf:logs:stream"
DLQ_STREAM_KEY = "waf:logs:dlq"
GROUP = "waf-log-ingest"
CONSUMER = "worker-1"
IDLE_SLEEP = 0.5
MAX_PERSIST_RETRIES = 3

_last_bot_catalog_refresh = 0.0


async def _ensure_group(redis) -> None:
    try:
        await redis.xgroup_create(STREAM_KEY, GROUP, id="0", mkstream=True)
    except Exception as exc:  # noqa: BLE001
        if "BUSYGROUP" not in str(exc):
            log.debug("xgroup_create: %s", exc)


def _parse_entry(fields: dict) -> dict | None:
    raw = fields.get("data") or fields.get(b"data")
    if raw is None and len(fields) == 1:
        raw = next(iter(fields.values()))
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


async def _read_stream_batch(redis, *, count: int, block_ms: int) -> list[tuple[str, dict]]:
    resp = await redis.xreadgroup(
        GROUP, CONSUMER, {STREAM_KEY: ">"}, count=count, block=block_ms
    )
    if not resp:
        return []
    out = []
    for _stream, messages in resp:
        for msg_id, fields in messages:
            if isinstance(msg_id, bytes):
                msg_id = msg_id.decode()
            parsed_fields = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else v
                )
                for k, v in fields.items()
            }
            out.append((msg_id, parsed_fields))
    return out


async def _drain_stream_batch(redis) -> list[tuple[str, dict]]:
    """Read up to batch_size * max_drain_batches messages when backlog exists."""
    batch_size = settings.log_collector_batch_size
    max_batches = max(1, settings.log_collector_max_drain_batches)
    max_entries = batch_size * max_batches
    collected: list[tuple[str, dict]] = []

    for batch_idx in range(max_batches):
        remaining = max_entries - len(collected)
        if remaining <= 0:
            break
        block_ms = 1000 if batch_idx == 0 else 0
        chunk = await _read_stream_batch(
            redis,
            count=min(batch_size, remaining),
            block_ms=block_ms,
        )
        if not chunk:
            break
        collected.extend(chunk)
        if len(chunk) < batch_size:
            break
    return collected


async def _maybe_refresh_bot_catalog(redis) -> None:
    global _last_bot_catalog_refresh

    interval = max(5, settings.log_collector_bot_catalog_refresh_sec)
    now = time.monotonic()
    if now - _last_bot_catalog_refresh < interval:
        return
    await refresh_from_redis(redis)
    _last_bot_catalog_refresh = now


async def _send_dlq(redis, msg_id: str, error: str, fields: dict | None = None) -> None:
    payload: dict = {"msg_id": msg_id, "error": error}
    if fields is not None:
        payload["fields"] = fields
    await redis.xadd(DLQ_STREAM_KEY, {"data": json.dumps(payload, default=str)})


async def _ack_messages(redis, msg_ids: list[str]) -> None:
    if msg_ids:
        await redis.xack(STREAM_KEY, GROUP, *msg_ids)


async def run_consumer(stop_event: asyncio.Event | None = None) -> None:
    redis = get_redis()
    store = ClickHouseLogStore()
    await store.ensure_schema()
    await _ensure_group(redis)
    from app.services.logging.clickhouse_patches import ensure_hourly_mv_state

    await asyncio.to_thread(ensure_hourly_mv_state)
    await refresh_from_redis(redis)
    global _last_bot_catalog_refresh
    _last_bot_catalog_refresh = time.monotonic()
    log.info(
        "log collector started (clickhouse batch_size=%d max_drain_batches=%d)",
        settings.log_collector_batch_size,
        settings.log_collector_max_drain_batches,
    )

    while stop_event is None or not stop_event.is_set():
        await _maybe_refresh_bot_catalog(redis)
        stream_msgs = await _drain_stream_batch(redis)
        if not stream_msgs:
            continue

        entries: list[dict] = []
        ack_ids: list[str] = []

        for msg_id, fields in stream_msgs:
            entry = _parse_entry(fields)
            if entry:
                entries.append(entry)
                ack_ids.append(msg_id)
            else:
                log.warning("malformed log stream message %s, moving to dlq", msg_id)
                await _send_dlq(redis, msg_id, "parse_failed", fields)
                await _ack_messages(redis, [msg_id])

        if not entries:
            continue

        persisted = False
        for attempt in range(MAX_PERSIST_RETRIES):
            try:
                await store.add_many(entries)
                await _ack_messages(redis, ack_ids)
                log.debug("persisted %d log entries", len(entries))
                persisted = True
                break
            except Exception:  # noqa: BLE001
                log.exception(
                    "failed to persist log batch (attempt %d/%d)",
                    attempt + 1,
                    MAX_PERSIST_RETRIES,
                )
                if attempt < MAX_PERSIST_RETRIES - 1:
                    await asyncio.sleep(IDLE_SLEEP * (attempt + 1))

        if not persisted:
            for msg_id in ack_ids:
                await _send_dlq(redis, msg_id, "persist_failed")
            await _ack_messages(redis, ack_ids)
            log.error("gave up on batch of %d messages after dlq", len(ack_ids))
            await asyncio.sleep(IDLE_SLEEP)
