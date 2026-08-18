"""Apply AI-generated rules with safety guards."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.fields import validate_condition
from app.services.ai_guard.config import AiGuardRuntimeConfig
from app.services.ai_guard.mode_guide import normalize_action_mode, normalize_apply_mode
from app.services.ai_guard.ports import writer

log = logging.getLogger("waf.ai_guard.applier")


def resolve_effective_mode(
    *,
    apply_mode: str,
    draft_mode: str | None,
    analysis: dict | None,
    min_confidence: float,
) -> str:
    """Pick the engine action for an auto-created rule.

    auto_observe always writes observe. auto_handle keeps the AI-chosen mode
    among observe/block/js_challenge/slide_captcha, but non-observe actions
    require confidence >= min_confidence (prefer false negatives).
    """
    mode = normalize_apply_mode(apply_mode)
    chosen = normalize_action_mode(draft_mode)
    if mode == "auto_observe":
        return "observe"
    if mode != "auto_handle":
        return chosen
    if chosen == "observe":
        return "observe"
    confidence = float((analysis or {}).get("confidence") or 0)
    if confidence >= min_confidence:
        return chosen
    log.info(
        "auto_handle guard: mode=%s confidence=%.2f < %.2f -> observe",
        chosen,
        confidence,
        min_confidence,
    )
    return "observe"


async def apply_rule_draft(
    db: AsyncSession,
    draft: dict,
    *,
    apply_mode: str,
    config: AiGuardRuntimeConfig,
    analysis: dict | None = None,
) -> tuple[int | None, str]:
    """Returns (rule_id or None, effective_mode)."""
    mode = normalize_apply_mode(apply_mode)
    if mode == "suggest_only":
        return None, "suggest_only"

    effective = resolve_effective_mode(
        apply_mode=mode,
        draft_mode=draft.get("mode"),
        analysis=analysis,
        min_confidence=config.auto_block_min_confidence,
    )

    payload = {
        "name": draft.get("name") or "防护规则",
        "mode": effective,
        "priority": draft.get("priority", 100),
        "site_ids": draft.get("site_ids"),
        "enabled": draft.get("enabled", True),
        "conditions": draft.get("conditions"),
    }
    validate_condition(payload.get("conditions"))
    result = await writer.create_rule(db, payload)
    return int(result["id"]), effective


async def check_rule_conflicts(db: AsyncSession, draft: dict) -> list[str]:
    """Detect potential conflicts with existing rules at same priority."""
    from sqlalchemy import select

    from app.models import Rule

    priority = int(draft.get("priority") or 100)
    site_ids = draft.get("site_ids") or []
    rows = (
        await db.execute(select(Rule).where(Rule.priority == priority).limit(20))
    ).scalars().all()
    warnings = []
    for r in rows:
        r_sites = r.site_ids or []
        if not site_ids or not r_sites or set(site_ids) & set(r_sites):
            warnings.append(f"与规则 #{r.id}「{r.name}」优先级相同 ({priority})")
    return warnings
