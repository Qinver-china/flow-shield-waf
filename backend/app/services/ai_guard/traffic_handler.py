"""Traffic intel hook: trigger AI defense on anomaly."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_guard.config import is_defense_enabled
from app.services.ai_guard.defense.pipeline import run_defense_for_policy
from app.services.ai_guard.defense.trigger_eval import evaluate_policy, list_enabled_policies
from app.services.traffic_intel.actions.handlers import ActionHandler
from app.services.traffic_intel.types import AnomalyResult, TrafficIntelConfig

log = logging.getLogger("waf.ai_guard.traffic_handler")


class AiGuardTrafficHandler(ActionHandler):
    """Optional ActionHandler — runs AI defense when traffic_intel detects anomaly."""

    async def handle(
        self,
        db: AsyncSession,
        anomaly: AnomalyResult,
        config: TrafficIntelConfig,
    ) -> None:
        if not await is_defense_enabled(db):
            return
        policies = await list_enabled_policies(db)
        for policy in policies:
            if policy.trigger_type != "traffic_intel.anomaly":
                continue
            snapshot = await evaluate_policy(db, policy, anomaly=anomaly)
            if snapshot is None:
                continue
            try:
                await run_defense_for_policy(
                    db,
                    policy,
                    trigger_snapshot=snapshot,
                    site_id=anomaly.site_id,
                )
            except Exception:  # noqa: BLE001
                log.exception("ai guard traffic handler policy=%s failed", policy.id)
