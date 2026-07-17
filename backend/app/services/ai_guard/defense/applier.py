"""Apply AI-generated rules with safety guards."""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.fields import validate_condition
from app.models.rule import MODES
from app.services.ai_guard.config import AiGuardRuntimeConfig
from app.services.ai_guard.ports import writer

log = logging.getLogger("waf.ai_guard.applier")


async def apply_rule_draft(
    db: AsyncSession,
    draft: dict,
    *,
    apply_mode: str,
    config: AiGuardRuntimeConfig,
    analysis: dict | None = None,
) -> tuple[int | None, str]:
    """Returns (rule_id or None, effective_mode)."""
    if apply_mode == "suggest_only":
        return None, "suggest_only"

    mode = draft.get("mode", "observe")
    if apply_mode == "auto_observe":
        mode = "observe"
    elif apply_mode == "auto_block":
        confidence = float((analysis or {}).get("confidence") or 0)
        blocked_ratio = float((analysis or {}).get("blocked_ratio") or 0)
        if confidence >= config.auto_block_min_confidence and blocked_ratio >= 0.5:
            mode = "block"
        else:
            mode = "observe"
            log.info(
                "auto_block guard: confidence=%.2f blocked_ratio=%.2f -> observe",
                confidence,
                blocked_ratio,
            )

    if mode not in MODES:
        mode = "observe"

    payload = {
        "name": draft.get("name") or "AI 防护规则",
        "mode": mode,
        "priority": draft.get("priority", 100),
        "site_ids": draft.get("site_ids"),
        "enabled": draft.get("enabled", True),
        "conditions": draft.get("conditions"),
    }
    validate_condition(payload.get("conditions"))
    result = await writer.create_rule(db, payload)
    return int(result["id"]), mode


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
