"""Tests for AI Guard defense rule generator (multi-turn)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai_guard.config import AiGuardRuntimeConfig
from app.services.ai_guard.defense.rule_generator import analyze_and_suggest
from app.services.ai_guard.llm.schemas import AttackAnalysis


def _test_config() -> AiGuardRuntimeConfig:
    return AiGuardRuntimeConfig(
        enabled=True,
        provider_base_url="https://example.com/v1",
        api_key="test-key",
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=4096,
        chat_enabled=True,
        defense_enabled=True,
        defense_web_search_enabled=False,
        default_apply_mode="suggest_only",
        max_logs_per_analysis=200,
        analysis_cooldown_sec=300,
        auto_block_min_confidence=0.85,
    )


def _submit_tool_call(args: dict) -> dict:
    return {
        "id": "call_submit",
        "type": "function",
        "function": {
            "name": "submit_analysis",
            "arguments": json.dumps(args, ensure_ascii=False),
        },
    }


@pytest.mark.asyncio
async def test_analyze_and_suggest_multiround_with_submit():
    cfg = _test_config()
    submit_args = {
        "summary": "正常流量尖峰",
        "attack_indicators": [],
        "benign_indicators": ["搜索引擎爬虫"],
        "confidence": 0.4,
        "create_rule": False,
        "evidence": [],
    }

    with (
        patch(
            "app.services.ai_guard.defense.rule_generator.build_knowledge_snapshot",
            new_callable=AsyncMock,
            return_value={
                "field_catalog": {},
                "defense": {},
                "sites": [{"id": 7, "name": "demo", "domains": ["demo.test"]}],
            },
        ),
        patch(
            "app.services.ai_guard.defense.rule_generator.build_defense_traffic_overview",
            new_callable=AsyncMock,
            return_value={
                "global": {"windows": [{"window_sec": 60, "requests": 120, "qps": 2.0}]},
                "sites": [
                    {
                        "site_id": 7,
                        "name": "demo",
                        "windows": [{"window_sec": 60, "requests": 100, "qps": 1.67}],
                    }
                ],
            },
        ),
        patch("app.services.ai_guard.defense.rule_generator.LlmClient") as client_cls,
    ):
        client = client_cls.return_value
        client.chat_completion = AsyncMock(
            side_effect=[
                {
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_q1",
                            "type": "function",
                            "function": {
                                "name": "get_log_stats",
                                "arguments": json.dumps({"hours": 2}),
                            },
                        }
                    ],
                },
                {
                    "content": "",
                    "tool_calls": [_submit_tool_call(submit_args)],
                },
            ]
        )

        with patch(
            "app.services.ai_guard.defense.rule_generator.run_defense_tool_calls",
            new_callable=AsyncMock,
            side_effect=[
                (
                    [{"role": "tool", "tool_call_id": "call_q1", "content": '{"total": 10}'}],
                    None,
                ),
                (
                    [{"role": "tool", "tool_call_id": "call_submit", "content": "{}"}],
                    AttackAnalysis.model_validate(submit_args),
                ),
            ],
        ):
            result = await analyze_and_suggest(
                db=AsyncMock(),
                config=cfg,
                log_rows=[{"request_id": "r1", "client_ip": "1.2.3.4", "blocked": False}],
                log_meta={
                    "sampled": 1,
                    "window_min": 30,
                    "sample_scope": "passed_only",
                    "query_hint": "expand if needed",
                },
                site_id=7,
                custom_prompt="勿封 CDN",
                trigger_snapshot={"type": "traffic.qps_gt", "window_sec": 60},
            )

    assert result.create_rule is False
    assert result.suggested_rule is None
    assert client.chat_completion.await_count == 2
    first_tools = client.chat_completion.await_args_list[0].kwargs["tools"]
    assert all(tool["function"]["name"] != "web_search" for tool in first_tools)
    first_messages = client.chat_completion.await_args_list[0].args[0]
    payload = json.loads(first_messages[1]["content"])
    assert payload["custom_prompt"] == "勿封 CDN"
    assert payload["initial_sample"]["sample_scope"] == "passed_only"
    assert payload["trigger"]["type"] == "traffic.qps_gt"
    assert payload["sites"][0]["id"] == 7
    assert payload["traffic_overview"]["sites"][0]["site_id"] == 7
    assert payload["traffic_overview"]["global"]["windows"][0]["qps"] == 2.0


@pytest.mark.asyncio
async def test_analyze_and_suggest_submit_with_rule():
    cfg = _test_config()
    submit_args = {
        "summary": "扫描器",
        "attack_indicators": ["异常 UA"],
        "benign_indicators": [],
        "confidence": 0.9,
        "create_rule": True,
        "suggested_rule": {
            "name": "封禁扫描 UA",
            "mode": "observe",
            "priority": 100,
            "site_ids": [],
            "conditions": {"field": "http.ua", "op": "contains", "value": "scanner"},
        },
        "evidence": [],
    }

    with (
        patch(
            "app.services.ai_guard.defense.rule_generator.build_knowledge_snapshot",
            new_callable=AsyncMock,
            return_value={"field_catalog": {}, "defense": {}, "sites": []},
        ),
        patch(
            "app.services.ai_guard.defense.rule_generator.build_defense_traffic_overview",
            new_callable=AsyncMock,
            return_value={"global": {"windows": []}, "sites": []},
        ),
        patch("app.services.ai_guard.defense.rule_generator.LlmClient") as client_cls,
        patch(
            "app.services.ai_guard.defense.rule_generator.run_defense_tool_calls",
            new_callable=AsyncMock,
            return_value=(
                [{"role": "tool", "tool_call_id": "call_submit", "content": "{}"}],
                AttackAnalysis.model_validate(submit_args),
            ),
        ),
    ):
        client = client_cls.return_value
        client.chat_completion = AsyncMock(
            return_value={
                "content": "",
                "tool_calls": [_submit_tool_call(submit_args)],
            }
        )

        result = await analyze_and_suggest(
            db=AsyncMock(),
            config=cfg,
            log_rows=[],
            log_meta={"sampled": 0, "window_min": 30, "sample_scope": "passed_only"},
        )

    assert result.create_rule is True
    assert result.suggested_rule is not None
    assert result.suggested_rule.name == "封禁扫描 UA"
