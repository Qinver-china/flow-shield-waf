"""AI Guard background worker loop."""
from __future__ import annotations

import asyncio
import logging
import time

from app.core.db import SessionLocal
from app.services.ai_guard.config import is_defense_enabled, load_runtime_config
from app.services.ai_guard.defense.pipeline import run_defense_for_policy
from app.services.ai_guard.defense.trigger_eval import evaluate_policy, list_enabled_policies

log = logging.getLogger("waf.ai_guard.worker")

LOOP_INTERVAL_SEC = 5
_last_global_run_at = 0.0


async def run_ai_guard_loop(stop_event=None) -> None:
    global _last_global_run_at
    log.info("ai guard worker started (interval=%ss)", LOOP_INTERVAL_SEC)
    while stop_event is None or not stop_event.is_set():
        try:
            async with SessionLocal() as db:
                if not await is_defense_enabled(db):
                    pass
                else:
                    cfg = await load_runtime_config(db)
                    now = time.monotonic()
                    if now - _last_global_run_at < cfg.analysis_cooldown_sec:
                        pass
                    else:
                        policies = await list_enabled_policies(db)
                        for policy in policies:
                            if policy.trigger_type == "traffic_intel.anomaly":
                                continue
                            snapshot = await evaluate_policy(db, policy)
                            if snapshot is None:
                                continue
                            site_id = snapshot.get("site_id")
                            try:
                                await run_defense_for_policy(
                                    db,
                                    policy,
                                    trigger_snapshot=snapshot,
                                    site_id=site_id,
                                )
                                _last_global_run_at = time.monotonic()
                                log.info("ai guard policy %s triggered", policy.id)
                                break
                            except Exception:  # noqa: BLE001
                                _last_global_run_at = time.monotonic()
                                log.exception("ai guard policy %s run failed", policy.id)
                                break
        except Exception:  # noqa: BLE001
            log.exception("ai guard worker tick failed")

        if stop_event is not None:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=LOOP_INTERVAL_SEC)
                break
            except TimeoutError:
                continue
        else:
            await asyncio.sleep(LOOP_INTERVAL_SEC)
