"""AI Guard chat ownership tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_guard.chat.service import ChatService


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
