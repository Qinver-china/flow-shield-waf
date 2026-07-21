"""Evaluate whether AI Guard policies should fire."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.alert_conditions import CONDITION_TYPE_MAP
from app.models.ai_guard import AiGuardPolicy
from app.services.ai_guard.defense.triggers import normalize_legacy_trigger_params
from app.services.notifications.evaluator import AlertPolicyEvaluator
from app.services.traffic_intel.types import AnomalyResult

log = logging.getLogger("waf.ai_guard.trigger")

_alert_evaluator = AlertPolicyEvaluator()


def _in_cooldown(policy: AiGuardPolicy) -> bool:
    if not policy.last_triggered_at:
        return False
    return datetime.utcnow() - policy.last_triggered_at < timedelta(seconds=policy.cooldown_sec)


def _matches_filter(policy: AiGuardPolicy, site_id: int | None) -> bool:
    filt = policy.condition_filter or {}
    want_site = filt.get("site_id")
    if want_site is not None and site_id is not None and int(want_site) != site_id:
        return False
    if want_site is not None and site_id is None:
        return False
    return True


def _analysis_window_min(params: dict, *, fallback: int = 5) -> int:
    """Derive log-sampling window minutes from trigger params."""
    if params.get("window_min") not in (None, ""):
        return max(1, int(params["window_min"]))
    if params.get("window_sec") not in (None, ""):
        return max(1, int(params["window_sec"]) // 60 or 1)
    return fallback


def _snapshot_from_hit(
    *,
    trigger_type: str,
    params: dict,
    message: str | None = None,
    extra: dict | None = None,
) -> dict:
    """Build the trigger snapshot consumed by the defense pipeline."""
    snapshot: dict = {
        "type": trigger_type,
        "window_min": _analysis_window_min(params),
        "site_id": params.get("site_id"),
    }
    if params.get("window_sec") not in (None, ""):
        snapshot["window_sec"] = int(params["window_sec"])
    if params.get("threshold") not in (None, ""):
        snapshot["threshold"] = params["threshold"]
    if params.get("percent") not in (None, ""):
        snapshot["percent"] = params["percent"]
    if message:
        snapshot["message"] = message
    if extra:
        snapshot.update(extra)
    return snapshot


async def evaluate_policy(
    db: AsyncSession, policy: AiGuardPolicy, *, anomaly: AnomalyResult | None = None
) -> dict | None:
    """Return a trigger snapshot when ``policy`` should fire, else ``None``."""
    if not policy.enabled or _in_cooldown(policy):
        return None

    params = normalize_legacy_trigger_params(policy.trigger_type, policy.trigger_params)
    ttype = policy.trigger_type

    if ttype == "traffic_intel.anomaly":
        if anomaly is None:
            return None
        want = params.get("window_sec")
        if want not in (None, "") and int(want) != anomaly.window_sec:
            return None
        site_id = anomaly.site_id
        want_site = params.get("site_id")
        if want_site not in (None, "") and site_id is not None and int(want_site) != int(site_id):
            return None
        if want_site not in (None, "") and site_id is None:
            return None
        if not _matches_filter(policy, site_id):
            return None
        return _snapshot_from_hit(
            trigger_type=ttype,
            params={**params, "window_sec": anomaly.window_sec, "site_id": site_id},
            message=anomaly.message,
            extra={
                "current_requests": anomaly.current_requests,
                "baseline_avg": anomaly.baseline_avg,
            },
        )

    if ttype not in CONDITION_TYPE_MAP:
        log.warning("unsupported ai guard trigger type: %s", ttype)
        return None

    fake_alert = SimpleNamespace(
        name=policy.name,
        condition_type=ttype,
        condition_params=params,
    )
    message = await _alert_evaluator._evaluate(fake_alert, db)  # noqa: SLF001
    if not message:
        return None

    site_id = params.get("site_id")
    if not _matches_filter(policy, site_id if site_id is not None else None):
        return None

    return _snapshot_from_hit(trigger_type=ttype, params=params, message=message)


async def list_enabled_policies(db: AsyncSession) -> list[AiGuardPolicy]:
    return list(
        (
            await db.execute(
                select(AiGuardPolicy)
                .where(AiGuardPolicy.enabled.is_(True))
                .order_by(AiGuardPolicy.id)
            )
        ).scalars().all()
    )
