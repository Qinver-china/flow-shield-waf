"""Tool execution for automated defense analysis (read-only + submit)."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_guard.context.tools import DEFENSE_READ_TOOL_NAMES
from app.services.ai_guard.llm.schemas import AttackAnalysis
from app.services.ai_guard.ports import writer

log = logging.getLogger("waf.ai_guard.defense.tools")

SUBMIT_ANALYSIS_TOOL = "submit_analysis"
_TOOL_RESULT_MAX_CHARS = 14000


def _encode_tool_result(data: Any) -> str:
    content = json.dumps(data, ensure_ascii=False, default=str)
    if len(content) <= _TOOL_RESULT_MAX_CHARS:
        return content
    return content[:_TOOL_RESULT_MAX_CHARS] + "...(truncated)"


async def run_defense_tool_calls(
    db: AsyncSession,
    tool_calls: list[dict],
    *,
    allow_web_search: bool = False,
) -> tuple[list[dict], AttackAnalysis | None]:
    """Run enabled defense-phase tools and return messages plus optional analysis.

    @param db: Active database session.
    @param tool_calls: Tool calls returned by the model.
    @param allow_web_search: Whether external search is enabled for this run.
    @return: Encoded tool messages and an optional submitted analysis.
    """
    results: list[dict] = []
    analysis: AttackAnalysis | None = None
    allowed_tools = DEFENSE_READ_TOOL_NAMES
    if not allow_web_search:
        allowed_tools = allowed_tools - {"web_search"}

    for tc in tool_calls:
        fn = tc.get("function") or {}
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}

        if name == SUBMIT_ANALYSIS_TOOL:
            try:
                analysis = AttackAnalysis.model_validate(args)
                results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": json.dumps(
                            {"status": "accepted", "create_rule": analysis.create_rule},
                            ensure_ascii=False,
                        ),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("submit_analysis validation failed: %s", exc)
                results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                    }
                )
            continue

        if name not in allowed_tools:
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps(
                        {"error": f"防御分析阶段不可用工具: {name}"},
                        ensure_ascii=False,
                    ),
                }
            )
            continue

        try:
            data = await writer.execute_tool(db, name, args)
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": _encode_tool_result(data),
                }
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("defense tool %s failed: %s", name, exc)
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                }
            )

    return results, analysis
