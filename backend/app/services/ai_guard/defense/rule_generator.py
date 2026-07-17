"""LLM-based log analysis and rule generation."""
from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_guard.config import AiGuardRuntimeConfig
from app.services.ai_guard.context.builder import build_knowledge_snapshot
from app.services.ai_guard.llm.client import LlmClient
from app.services.ai_guard.llm.prompts import DEFENSE_SYSTEM
from app.services.ai_guard.llm.schemas import AttackAnalysis
from app.services.ai_guard.ports import compact_log_rows

log = logging.getLogger("waf.ai_guard.rule_generator")


async def analyze_and_suggest(
    db: AsyncSession,
    config: AiGuardRuntimeConfig,
    *,
    log_rows: list[dict],
    log_meta: dict,
    site_id: int | None = None,
) -> AttackAnalysis:
    client = LlmClient(config)
    snapshot = await build_knowledge_snapshot(db)
    compact = compact_log_rows(log_rows, limit=80)

    user_content = json.dumps(
        {
            "site_id": site_id,
            "log_meta": log_meta,
            "blocked_ratio": round(
                log_meta.get("blocked_count", 0) / max(log_meta.get("sampled", 1), 1), 3
            ),
            "samples": compact,
            "field_catalog_summary": snapshot.get("field_catalog", {}).get("categories", [])[:8],
        },
        ensure_ascii=False,
        default=str,
    )

    messages = [
        {"role": "system", "content": DEFENSE_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    raw = await client.chat_json(messages, temperature=0.1)
    analysis = AttackAnalysis.model_validate(raw)
    return analysis
