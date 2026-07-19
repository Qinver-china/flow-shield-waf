"""AI Guard chat ownership tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_guard.chat.service import ChatService, _complete_with_tools, _history_to_messages


@pytest.mark.asyncio
async def test_history_to_messages_strips_tool_calls():
    row = MagicMock()
    row.role = "assistant"
    row.content = "已生成规则说明"
    row.tool_calls = [{"id": "tc1", "function": {"name": "preview_rule", "arguments": "{}"}}]
    assert _history_to_messages([row]) == [
        {"role": "assistant", "content": "已生成规则说明"},
    ]


@pytest.mark.asyncio
async def test_complete_with_tools_multi_round_read_only():
    client = AsyncMock()
    db = AsyncMock()
    messages = [{"role": "user", "content": "列出站点"}]
    client.chat_completion = AsyncMock(
        side_effect=[
            {
                "content": "",
                "tool_calls": [
                    {"id": "tc1", "function": {"name": "list_sites", "arguments": "{}"}},
                ],
            },
            {"content": "当前共有 2 个站点。", "tool_calls": None},
        ]
    )
    with patch(
        "app.services.ai_guard.chat.service._run_tools",
        AsyncMock(
            return_value=(
                [{"role": "tool", "tool_call_id": "tc1", "content": '{"sites": []}'}],
                [],
            )
        ),
    ):
        content, tool_calls, pending = await _complete_with_tools(client, db, messages)

    assert content == "当前共有 2 个站点。"
    assert tool_calls is not None
    assert pending is None
    assert client.chat_completion.await_count == 2


@pytest.mark.asyncio
async def test_complete_with_tools_pending_write_summary():
    client = AsyncMock()
    db = AsyncMock()
    messages = [{"role": "user", "content": "创建规则"}]
    client.chat_completion = AsyncMock(
        side_effect=[
            {
                "content": "",
                "tool_calls": [
                    {
                        "id": "tc1",
                        "function": {
                            "name": "create_rule",
                            "arguments": '{"name":"x","mode":"observe","conditions":{"field":"ip.src","op":"eq","value":"1.1.1.1"}}',
                        },
                    },
                ],
            },
            {"content": "已生成规则草案，请确认。", "tool_calls": None},
        ]
    )
    pending_item = {
        "tool": "create_rule",
        "arguments": {"name": "x"},
        "preview": {"valid": True},
    }
    with patch(
        "app.services.ai_guard.chat.service._run_tools",
        AsyncMock(
            return_value=(
                [{"role": "tool", "tool_call_id": "tc1", "content": "{}"}],
                [pending_item],
            )
        ),
    ):
        content, _tool_calls, pending = await _complete_with_tools(client, db, messages)

    assert content == "已生成规则草案，请确认。"
    assert pending == pending_item
    assert client.chat_completion.await_count == 2


@pytest.mark.asyncio
async def test_complete_with_tools_empty_fallback():
    client = AsyncMock()
    client.chat_completion = AsyncMock(return_value={"content": "", "tool_calls": None})
    content, _tool_calls, pending = await _complete_with_tools(client, AsyncMock(), [])
    assert pending is None
    assert "未能生成" in content


@pytest.mark.asyncio
async def test_confirm_action_rejects_foreign_session():
    service = ChatService()
    db = AsyncMock()
    message = MagicMock()
    message.pending_action = {"tool": "create_rule", "arguments": {}}
    message.session_id = 9
    session = MagicMock()
    session.user_id = 2

    with (
        patch.object(db, "get", AsyncMock(side_effect=[message, session])),
        pytest.raises(ValueError, match="无权访问该会话"),
    ):
        await service.confirm_action(
            db,
            user_id=1,
            message_id=100,
            approved=True,
        )


@pytest.mark.asyncio
async def test_confirm_action_validates_edited_payload():
    service = ChatService()
    db = AsyncMock()
    message = MagicMock()
    message.pending_action = {"tool": "create_rule", "arguments": {"name": "x"}}
    message.session_id = 9
    session = MagicMock()
    session.user_id = 1

    with (
        patch.object(db, "get", AsyncMock(side_effect=[message, session])),
        patch(
            "app.services.ai_guard.chat.service.writer.validate_tool_arguments",
            AsyncMock(side_effect=ValueError("bad payload")),
        ),
        pytest.raises(ValueError, match="bad payload"),
    ):
        await service.confirm_action(
            db,
            user_id=1,
            message_id=100,
            approved=True,
            edited_payload={"name": "evil"},
        )
