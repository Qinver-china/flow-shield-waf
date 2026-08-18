from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_guard.chat.service import enrich_pending_created_rules
from app.services.ai_guard.defense import pipeline
from app.services.ai_guard.defense.applier import resolve_effective_mode
from app.services.ai_guard.mode_guide import normalize_apply_mode
from app.services.ai_guard.ports import (
    AiResourceWriter,
    _bounded_list_limit,
    _sanitize_web_search_query,
    apply_ai_rule_name_prefix,
)


def test_apply_ai_rule_name_prefix():
    assert apply_ai_rule_name_prefix("扫描器") == "[AI规则]扫描器"
    assert apply_ai_rule_name_prefix("[AI规则]已有") == "[AI规则]已有"
    assert apply_ai_rule_name_prefix("  ") == "[AI规则]防护规则"


def test_normalize_apply_mode_aliases_auto_block():
    assert normalize_apply_mode("auto_block") == "auto_handle"
    assert normalize_apply_mode("auto_handle") == "auto_handle"


def test_resolve_effective_mode_prefers_false_negative():
    assert (
        resolve_effective_mode(
            apply_mode="auto_observe",
            draft_mode="block",
            analysis={"confidence": 0.99},
            min_confidence=0.85,
        )
        == "observe"
    )
    assert (
        resolve_effective_mode(
            apply_mode="auto_handle",
            draft_mode="js_challenge",
            analysis={"confidence": 0.9},
            min_confidence=0.85,
        )
        == "js_challenge"
    )
    assert (
        resolve_effective_mode(
            apply_mode="auto_handle",
            draft_mode="block",
            analysis={"confidence": 0.5},
            min_confidence=0.85,
        )
        == "observe"
    )
    assert (
        resolve_effective_mode(
            apply_mode="auto_block",
            draft_mode="slide_captcha",
            analysis={"confidence": 0.95},
            min_confidence=0.85,
        )
        == "slide_captcha"
    )


@pytest.mark.asyncio
async def test_preview_rule_rejects_empty_block_conditions():
    writer = AiResourceWriter()
    with pytest.raises(ValueError, match="条件不能为空"):
        await writer.preview_rule({"name": "x", "mode": "block", "conditions": {}})


@pytest.mark.asyncio
async def test_preview_rule_allows_empty_observe_conditions():
    writer = AiResourceWriter()
    result = await writer.preview_rule({"name": "x", "mode": "observe", "conditions": {}})
    assert result["valid"] is True
    assert result["mode"] == "observe"


@pytest.mark.asyncio
async def test_update_rule_validation_rejects_string_boolean():
    writer = AiResourceWriter()
    with pytest.raises(ValueError, match="enabled 必须是布尔值"):
        await writer.validate_tool_arguments("update_rule", {"id": 1, "enabled": "false"})


def test_list_limit_is_bounded_server_side():
    assert _bounded_list_limit(-1) == 1
    assert _bounded_list_limit(1000) == 100


def test_web_search_query_redacts_sensitive_values():
    query = _sanitize_web_search_query(
        "https://internal.test/callback?token=secret 192.168.1.8 Bearer abc"
    )
    assert "secret" not in query
    assert "192.168.1.8" not in query
    assert "Bearer abc" not in query


@pytest.mark.asyncio
async def test_apply_incident_rule_promotes_suggest_only():
    incident = MagicMock()
    incident.suggested_rule = {
        "name": "x",
        "conditions": {"field": "ip.src", "op": "eq", "value": "1.1.1.1"},
    }
    incident.applied_rule_id = None
    incident.apply_mode = "suggest_only"
    incident.analysis_report = {"confidence": 0.9}

    cfg = MagicMock()
    cfg.default_apply_mode = "suggest_only"

    with (
        patch.object(pipeline, "_incidents") as store,
        patch(
            "app.services.ai_guard.defense.pipeline.load_runtime_config",
            AsyncMock(return_value=cfg),
        ),
        patch(
            "app.services.ai_guard.defense.pipeline.apply_rule_draft",
            AsyncMock(return_value=(42, "observe")),
        ) as apply_draft,
    ):
        store.get = AsyncMock(return_value=incident)
        store.upsert = AsyncMock(side_effect=lambda row: row)
        result = await pipeline.apply_incident_rule(AsyncMock(), 7)

    assert apply_draft.await_args.kwargs["apply_mode"] == "auto_handle"
    assert result.applied_rule_id == 42
    assert result.status == "applied"
    assert result.apply_mode == "observe"


@pytest.mark.asyncio
async def test_apply_incident_rule_does_not_mark_applied_without_id():
    incident = MagicMock()
    incident.suggested_rule = {"name": "x"}
    incident.applied_rule_id = None
    incident.apply_mode = "auto_observe"
    incident.analysis_report = {}
    incident.status = "suggested"

    cfg = MagicMock()
    cfg.default_apply_mode = "suggest_only"

    with (
        patch.object(pipeline, "_incidents") as store,
        patch(
            "app.services.ai_guard.defense.pipeline.load_runtime_config",
            AsyncMock(return_value=cfg),
        ),
        patch(
            "app.services.ai_guard.defense.pipeline.apply_rule_draft",
            AsyncMock(return_value=(None, "suggest_only")),
        ),
    ):
        store.get = AsyncMock(return_value=incident)
        with pytest.raises(ValueError, match="规则未能创建"):
            await pipeline.apply_incident_rule(AsyncMock(), 7)

    assert incident.status == "suggested"
    assert incident.applied_rule_id is None


@pytest.mark.asyncio
async def test_enrich_pending_created_rules_marks_missing():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    pending = {
        "tool": "create_rule",
        "created": [{"tool": "create_rule", "id": 9, "name": "[AI规则]x"}],
    }
    out = await enrich_pending_created_rules(db, pending)
    assert out["created"][0]["exists"] is False
    db.execute.assert_awaited_once()
