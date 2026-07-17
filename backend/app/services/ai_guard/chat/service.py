"""Chat orchestration: LLM + tool calls + pending actions."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardChatSession
from app.services.ai_guard.chat import session_store
from app.services.ai_guard.config import AiGuardRuntimeConfig, load_runtime_config
from app.services.ai_guard.context.builder import build_knowledge_snapshot
from app.services.ai_guard.context.tools import TOOL_DEFINITIONS, WRITE_TOOLS
from app.services.ai_guard.llm.client import LlmClient
from app.services.ai_guard.llm.prompts import CHAT_SYSTEM
from app.services.ai_guard.ports import writer

log = logging.getLogger("waf.ai_guard.chat")


def _history_to_messages(rows: list) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.role in ("user", "assistant", "system"):
            msg: dict[str, Any] = {"role": row.role, "content": row.content or ""}
            if row.tool_calls:
                msg["tool_calls"] = row.tool_calls
            out.append(msg)
    return out


async def _run_tools(
    db: AsyncSession, tool_calls: list[dict], *, dry_run_writes: bool
) -> tuple[list[dict], list[dict]]:
    """Returns (tool result messages, pending actions)."""
    results = []
    pending = []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        name = fn.get("name", "")
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        if name in WRITE_TOOLS and dry_run_writes:
            try:
                preview = await writer.execute_tool(db, name, args, dry_run=True)
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id"),
                        "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                    }
                )
                continue
            pending.append({"tool": name, "arguments": args, "preview": preview})
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps(
                        {"status": "pending_confirmation", "tool": name, "arguments": args},
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
                    "content": json.dumps(data, ensure_ascii=False, default=str),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "content": json.dumps({"error": str(exc)}, ensure_ascii=False),
                }
            )
    return results, pending


class ChatService:
    @staticmethod
    def _ensure_session_owner(sess: AiGuardChatSession | None, user_id: int | None) -> AiGuardChatSession:
        if sess is None:
            raise ValueError("会话不存在")
        if user_id is not None and sess.user_id not in (None, user_id):
            raise ValueError("无权访问该会话")
        return sess

    async def _get_owned_message(
        self,
        db: AsyncSession,
        *,
        message_id: int,
        user_id: int | None,
    ):
        from app.models.ai_guard import AiGuardChatMessage

        row = await db.get(AiGuardChatMessage, message_id)
        if row is None or not row.pending_action:
            raise ValueError("没有待确认的操作")
        sess = await db.get(AiGuardChatSession, row.session_id)
        self._ensure_session_owner(sess, user_id)
        return row, sess

    async def get_session_messages(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        session_id: int,
    ) -> list:
        sess = await db.get(AiGuardChatSession, session_id)
        self._ensure_session_owner(sess, user_id)
        return await session_store.get_messages(db, session_id)

    async def chat(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        session_id: int | None,
        message: str,
    ) -> dict:
        cfg = await load_runtime_config(db)
        if not cfg.enabled or not cfg.chat_enabled:
            raise ValueError("AI 聊天功能未启用")
        client = LlmClient(cfg)

        if session_id is None:
            sess = await session_store.create_session(db, user_id=user_id, title=message[:40])
            session_id = sess.id
        else:
            sess = await db.get(AiGuardChatSession, session_id)
            self._ensure_session_owner(sess, user_id)

        await session_store.add_message(db, session_id=session_id, role="user", content=message)
        history = await session_store.get_messages(db, session_id)
        snapshot = await build_knowledge_snapshot(db)

        messages = [
            {"role": "system", "content": CHAT_SYSTEM},
            {
                "role": "system",
                "content": "知识上下文：\n" + json.dumps(snapshot, ensure_ascii=False)[:12000],
            },
            *_history_to_messages(history),
        ]

        result = await client.chat_completion(messages, tools=TOOL_DEFINITIONS)
        content = result.get("content") or ""
        tool_calls = result.get("tool_calls")
        pending_action = None

        if tool_calls:
            tool_msgs, pending = await _run_tools(db, tool_calls, dry_run_writes=True)
            if pending:
                pending_action = pending[0] if len(pending) == 1 else {"actions": pending}
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})
            messages.extend(tool_msgs)
            follow = await client.chat_completion(messages, tools=TOOL_DEFINITIONS)
            content = follow.get("content") or content

        msg_row = await session_store.add_message(
            db,
            session_id=session_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            pending_action=pending_action,
            action_status="pending" if pending_action else None,
        )
        return {
            "session_id": session_id,
            "message": {
                "id": msg_row.id,
                "role": "assistant",
                "content": content,
                "pending_action": pending_action,
                "action_status": msg_row.action_status,
            },
        }

    async def stream_chat(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        session_id: int | None,
        message: str,
    ) -> AsyncIterator[str]:
        result = await self.chat(db, user_id=user_id, session_id=session_id, message=message)
        yield json.dumps({"type": "session", "session_id": result["session_id"]}, ensure_ascii=False)
        text = result["message"]["content"]
        chunk_size = 24
        for i in range(0, len(text), chunk_size):
            yield json.dumps({"type": "delta", "delta": text[i : i + chunk_size]}, ensure_ascii=False)
        yield json.dumps(
            {
                "type": "done",
                "message_id": result["message"]["id"],
                "pending_action": result["message"].get("pending_action"),
            },
            ensure_ascii=False,
        )

    async def confirm_action(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        message_id: int,
        approved: bool,
        edited_payload: dict | None = None,
    ) -> dict:
        row, _sess = await self._get_owned_message(db, message_id=message_id, user_id=user_id)
        if row.action_status == "executed":
            raise ValueError("该操作已执行")
        if not approved:
            await session_store.update_message_action(db, message_id, action_status="cancelled")
            return {"status": "cancelled"}

        pending = row.pending_action
        if "actions" in pending:
            results = []
            for act in pending["actions"]:
                args = edited_payload if edited_payload is not None else act.get("arguments", {})
                await writer.validate_tool_arguments(act["tool"], args)
                res = await writer.execute_tool(db, act["tool"], args)
                results.append(res)
            await session_store.update_message_action(db, message_id, action_status="executed")
            return {"status": "executed", "results": results}

        tool = pending.get("tool")
        args = edited_payload if edited_payload is not None else pending.get("arguments", {})
        if not tool:
            raise ValueError("无效待确认操作")
        await writer.validate_tool_arguments(tool, args)
        result = await writer.execute_tool(db, tool, args)
        await session_store.update_message_action(db, message_id, action_status="executed")
        return {"status": "executed", "result": result}


chat_service = ChatService()
