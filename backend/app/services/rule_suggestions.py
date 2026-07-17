"""Rule suggestions — migrated to AI Guard. Kept for backward-compatible API."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule_suggestion import RuleSuggestion

log = logging.getLogger("waf.rule_suggestions")

ANALYSIS_ENABLED = True


async def run_analysis(db: AsyncSession, *, site_id: int | None = None, hours: int = 24) -> int:
    """Legacy endpoint: redirects to AI Guard manual trigger guidance."""
    _ = site_id, hours
    log.info("rule suggestion /analyze — use AI Guard defense policies instead")
    return 0


async def list_suggestions(db: AsyncSession, limit: int = 50) -> list[RuleSuggestion]:
    rows = (
        await db.execute(
            select(RuleSuggestion).order_by(RuleSuggestion.id.desc()).limit(limit)
        )
    ).scalars().all()
    return list(rows)
