"""LLM-based log analysis and rule generation (multi-turn with tools)."""
from __future__ import annotations

import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai_guard.config import AiGuardRuntimeConfig
from app.services.ai_guard.context.builder import build_knowledge_snapshot, knowledge_for_defense
from app.services.ai_guard.context.tools import DEFENSE_TOOL_DEFINITIONS
from app.services.ai_guard.defense.tool_runner import SUBMIT_ANALYSIS_TOOL, run_defense_tool_calls
from app.services.ai_guard.llm.client import LlmClient
from app.services.ai_guard.llm.prompts import DEFENSE_SYSTEM
from app.services.ai_guard.llm.schemas import AttackAnalysis
from app.services.ai_guard.ports import DEFENSE_INITIAL_MAX_ROWS, DEFENSE_INITIAL_WINDOW_MIN, compact_log_rows

log = logging.getLogger("waf.ai_guard.rule_generator")

_MAX_DEFENSE_ROUNDS = 6


def _build_initial_payload(
    *,
    site_id: int | None,
    log_meta: dict,
    log_rows: list[dict],
    field_catalog: dict,
    defense: dict | None,
    custom_prompt: str | None,
    trigger_snapshot: dict | None,
) -> dict:
    prompt = (custom_prompt or "").strip()
    payload: dict = {
        "trigger": trigger_snapshot or {},
        "site_id": site_id,
        "initial_sample": {
            "window_min": log_meta.get("window_min", DEFENSE_INITIAL_WINDOW_MIN),
            "max_rows": DEFENSE_INITIAL_MAX_ROWS,
            "sample_scope": log_meta.get("sample_scope", "passed_only"),
            "query_hint": log_meta.get("query_hint"),
            "meta": log_meta,
            "samples": compact_log_rows(log_rows, limit=DEFENSE_INITIAL_MAX_ROWS),
        },
        "field_catalog": knowledge_for_defense(field_catalog),
        "defense": defense,
        "instructions": (
            "以上为策略触发时的首批放行日志样本。"
            "若证据不足，请调用 query_logs / get_log_stats / query_log_stats_group "
            "扩大 hours 或调整 blocked 等筛选后再下结论。"
            "分析完成后必须调用 submit_analysis；无需建规则时设 create_rule=false。"
        ),
    }
    if prompt:
        payload["custom_prompt"] = prompt
    return payload


async def _force_submit_analysis(
    client: LlmClient,
    messages: list[dict],
) -> AttackAnalysis:
    messages = [
        *messages,
        {
            "role": "user",
            "content": (
                "已达到最大分析轮次。请立即调用 submit_analysis 提交最终结论；"
                "若无需新建规则则 create_rule=false。"
            ),
        },
    ]
    result = await client.chat_completion(messages, tools=DEFENSE_TOOL_DEFINITIONS, temperature=0.1)
    tool_calls = result.get("tool_calls") or []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        if fn.get("name") != SUBMIT_ANALYSIS_TOOL:
            continue
        try:
            args = json.loads(fn.get("arguments") or "{}")
            return AttackAnalysis.model_validate(args)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"强制提交分析失败: {exc}") from exc
    raise ValueError("AI 未能在限定轮次内提交分析结论")


async def analyze_and_suggest(
    db: AsyncSession,
    config: AiGuardRuntimeConfig,
    *,
    log_rows: list[dict],
    log_meta: dict,
    site_id: int | None = None,
    custom_prompt: str | None = None,
    trigger_snapshot: dict | None = None,
) -> AttackAnalysis:
    client = LlmClient(config)
    snapshot = await build_knowledge_snapshot(db)
    field_catalog = snapshot.get("field_catalog") or {}

    initial = _build_initial_payload(
        site_id=site_id,
        log_meta=log_meta,
        log_rows=log_rows,
        field_catalog=field_catalog,
        defense=snapshot.get("defense"),
        custom_prompt=custom_prompt,
        trigger_snapshot=trigger_snapshot,
    )
    messages: list[dict] = [
        {"role": "system", "content": DEFENSE_SYSTEM},
        {"role": "user", "content": json.dumps(initial, ensure_ascii=False, default=str)},
    ]

    analysis: AttackAnalysis | None = None
    for round_idx in range(_MAX_DEFENSE_ROUNDS):
        result = await client.chat_completion(
            messages,
            tools=DEFENSE_TOOL_DEFINITIONS,
            temperature=0.1,
        )
        content = result.get("content") or ""
        tool_calls = result.get("tool_calls")

        if not tool_calls:
            if round_idx == _MAX_DEFENSE_ROUNDS - 1:
                break
            messages.append(
                {
                    "role": "user",
                    "content": "请继续分析：需要更多数据就调用查询工具，完成后调用 submit_analysis。",
                }
            )
            continue

        messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
        tool_msgs, analysis = await run_defense_tool_calls(db, tool_calls)
        messages.extend(tool_msgs)

        if analysis is not None:
            return analysis

        if round_idx == _MAX_DEFENSE_ROUNDS - 1:
            log.warning("defense analysis hit max tool rounds (%s)", _MAX_DEFENSE_ROUNDS)

    return await _force_submit_analysis(client, messages)
