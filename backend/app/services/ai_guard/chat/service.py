"""Chat orchestration: LLM + tool calls + pending actions."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardChatSession
from app.services.ai_guard.chat import session_store
from app.services.ai_guard.config import load_runtime_config
from app.services.ai_guard.context.builder import build_knowledge_snapshot
from app.services.ai_guard.context.tools import TOOL_DEFINITIONS, WRITE_TOOLS
from app.services.ai_guard.llm.client import LlmClient
from app.services.ai_guard.llm.errors import format_llm_error
from app.services.ai_guard.llm.prompts import CHAT_SYSTEM
from app.services.ai_guard.ports import writer

log = logging.getLogger("waf.ai_guard.chat")

# Cap tool rounds to bound latency and upstream cost.
_MAX_TOOL_ROUNDS = 5
_KNOWLEDGE_SNAPSHOT_MAX_CHARS = 14000
_TOOL_RESULT_MAX_CHARS = 14000
_EMPTY_REPLY = "抱歉，我暂时未能生成有效回复，请重试或换个说法。"
_PENDING_REPLY = "已生成待确认操作，请在下方的卡片中查看详情并确认是否执行。"

_TOOL_LABELS: dict[str, str] = {
    "list_sites": "列出站点",
    "list_rules": "列出防护规则",
    "list_rate_limits": "列出 CC 限速策略",
    "query_logs": "查询 WAF 日志",
    "get_log_stats": "统计日志概览",
    "query_log_stats_group": "按维度聚合统计",
    "create_site": "创建站点",
    "create_rule": "创建自定义规则",
    "create_rate_limit": "创建 CC 限速策略",
    "create_blacklist_entry": "创建黑名单",
    "create_whitelist_entry": "创建白名单",
    "create_exception": "创建防护例外",
    "preview_rule": "校验防护规则",
    "preview_rate_limit": "校验限速策略",
}


def _tool_label(name: str) -> str:
    return _TOOL_LABELS.get(name, name)


def _summarize_tool_result(tool: str, raw_content: str) -> str:
    try:
        data = json.loads(raw_content)
    except json.JSONDecodeError:
        return "已完成"
    if isinstance(data, dict) and data.get("error"):
        return f"失败：{data['error']}"
    if tool == "query_logs":
        return f"共 {data.get('total', 0)} 条，返回 {data.get('returned', 0)} 条样本"
    if tool == "get_log_stats":
        return f"总请求 {data.get('total', 0)}，拦截 {data.get('blocked', 0)}"
    if tool == "query_log_stats_group":
        items = data.get("items") or []
        return f"共 {data.get('group_total', len(items))} 个分组"
    if tool == "list_sites":
        return f"共 {len(data.get('sites') or [])} 个站点"
    if tool == "list_rules":
        return f"共 {len(data.get('rules') or [])} 条规则"
    if tool == "list_rate_limits":
        return f"共 {len(data.get('rate_limits') or [])} 条策略"
    if tool in WRITE_TOOLS:
        return "已生成待确认草案"
    return "已完成"


def _format_tool_args_summary(tool: str, args: dict) -> str:
    if not args:
        return ""
    parts: list[str] = []
    for key in ("hours", "site_id", "blocked", "keyword", "dimension", "limit", "name"):
        if key in args and args[key] not in (None, ""):
            parts.append(f"{key}={args[key]}")
    if tool == "query_logs" and args.get("filters"):
        parts.append(f"filters={len(args['filters'])} 项")
    return "，".join(parts[:4])


async def _emit_deltas(text: str, *, chunk_size: int = 16):
    for i in range(0, len(text), chunk_size):
        yield {"type": "delta", "delta": text[i : i + chunk_size]}


def _history_to_messages(rows: list) -> list[dict[str, Any]]:
    """Replay persisted turns for the LLM.

    Only role + content are sent. Historical tool_calls are omitted because we do
    not persist tool-role messages; replaying tool_calls without tool responses
    breaks OpenAI-compatible APIs on follow-up turns.
    """
    out: list[dict[str, Any]] = []
    for row in rows:
        if row.role in ("user", "assistant", "system"):
            out.append({"role": row.role, "content": row.content or ""})
    return out


def _encode_tool_result(data: Any) -> str:
    content = json.dumps(data, ensure_ascii=False, default=str)
    if len(content) <= _TOOL_RESULT_MAX_CHARS:
        return content
    return content[:_TOOL_RESULT_MAX_CHARS] + "...(truncated)"


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
                    "content": _encode_tool_result(data),
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


async def _complete_with_tools(
    client: LlmClient,
    db: AsyncSession,
    messages: list[dict[str, Any]],
) -> tuple[str, list | None, dict | None]:
    """Multi-round tool loop; stops early when write actions need confirmation."""
    content = ""
    last_tool_calls: list | None = None
    pending_action = None

    for round_idx in range(_MAX_TOOL_ROUNDS):
        result = await client.chat_completion(messages, tools=TOOL_DEFINITIONS)
        round_content = result.get("content") or ""
        if round_content:
            content = round_content
        tool_calls = result.get("tool_calls")
        if not tool_calls:
            break

        last_tool_calls = tool_calls
        tool_msgs, pending = await _run_tools(db, tool_calls, dry_run_writes=True)
        messages.append({"role": "assistant", "content": round_content, "tool_calls": tool_calls})
        messages.extend(tool_msgs)

        if pending:
            pending_action = pending[0] if len(pending) == 1 else {"actions": pending}
            summary = await client.chat_completion(messages)
            if summary.get("content"):
                content = summary["content"]
            break

        if round_idx == _MAX_TOOL_ROUNDS - 1:
            log.warning("AI chat hit max tool rounds (%s)", _MAX_TOOL_ROUNDS)

    if pending_action is None and last_tool_calls and not (content or "").strip():
        try:
            summary = await client.chat_completion(messages)
            if summary.get("content"):
                content = summary["content"]
        except Exception as exc:  # noqa: BLE001
            log.warning("AI chat final summary after tools failed: %s", exc)

    if not (content or "").strip():
        content = _PENDING_REPLY if pending_action else _EMPTY_REPLY
    return content, last_tool_calls, pending_action


async def _stream_complete_with_tools(
    client: LlmClient,
    db: AsyncSession,
    messages: list[dict[str, Any]],
) -> AsyncIterator[dict[str, Any]]:
    """Yield step/delta events; final event type=final carries persistence fields."""
    content = ""
    last_tool_calls: list | None = None
    pending_action = None

    for round_idx in range(_MAX_TOOL_ROUNDS):
        think_id = f"think-{round_idx}"
        yield {
            "type": "step",
            "id": think_id,
            "kind": "thinking",
            "label": "正在思考.." if round_idx == 0 else f"继续推理（第 {round_idx + 1} 轮）...",
            "status": "running",
        }

        round_content = ""
        tool_calls: list | None = None
        async for event in client.stream_completion(messages, tools=TOOL_DEFINITIONS):
            if event.get("event") == "delta":
                round_content += event.get("content") or ""
            elif event.get("event") == "done":
                round_content = event.get("content") or round_content
                tool_calls = event.get("tool_calls")

        yield {
            "type": "step",
            "id": think_id,
            "kind": "thinking",
            "label": "分析完成" if not tool_calls else "已确定下一步操作",
            "status": "done",
            "detail": round_content.strip()[:1200] if round_content.strip() else None,
        }

        if not tool_calls:
            async for delta_event in _emit_deltas(round_content):
                yield delta_event
            content = round_content
            yield {
                "type": "final",
                "content": content,
                "tool_calls": None,
                "pending_action": None,
            }
            return

        last_tool_calls = tool_calls
        for tc_idx, tc in enumerate(tool_calls):
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_step_id = f"tool-{round_idx}-{tc_idx}-{name}"
            detail = _format_tool_args_summary(name, args)
            yield {
                "type": "step",
                "id": tool_step_id,
                "kind": "tool",
                "label": f"调用工具：{_tool_label(name)}",
                "status": "running",
                "detail": detail or None,
                "tool": name,
            }

        tool_msgs, pending = await _run_tools(db, tool_calls, dry_run_writes=True)

        for tc_idx, (tc, tmsg) in enumerate(zip(tool_calls, tool_msgs)):
            fn = tc.get("function") or {}
            name = fn.get("name", "")
            raw = tmsg.get("content") or ""
            try:
                parsed = json.loads(raw)
                ok = "error" not in parsed
            except json.JSONDecodeError:
                ok = True
            tool_step_id = f"tool-{round_idx}-{tc_idx}-{name}"
            yield {
                "type": "step",
                "id": tool_step_id,
                "kind": "tool",
                "label": _tool_label(name),
                "status": "done" if ok else "error",
                "detail": _summarize_tool_result(name, raw),
                "tool": name,
            }

        messages.append({"role": "assistant", "content": round_content, "tool_calls": tool_calls})
        messages.extend(tool_msgs)

        if pending:
            pending_action = pending[0] if len(pending) == 1 else {"actions": pending}
            gen_id = f"generate-{round_idx}"
            yield {
                "type": "step",
                "id": gen_id,
                "kind": "generating",
                "label": "正在生成回复...",
                "status": "running",
            }
            async for delta in client.stream_chat(messages):
                content += delta
                yield {"type": "delta", "delta": delta}
            yield {
                "type": "step",
                "id": gen_id,
                "kind": "generating",
                "label": "回复已生成",
                "status": "done",
            }
            yield {
                "type": "final",
                "content": content,
                "tool_calls": last_tool_calls,
                "pending_action": pending_action,
            }
            return

        if round_idx == _MAX_TOOL_ROUNDS - 1:
            log.warning("AI chat hit max tool rounds (%s)", _MAX_TOOL_ROUNDS)

    if pending_action is None and last_tool_calls and not (content or "").strip():
        gen_id = "generate-final"
        yield {
            "type": "step",
            "id": gen_id,
            "kind": "generating",
            "label": "正在整理结论...",
            "status": "running",
        }
        try:
            async for delta in client.stream_chat(messages):
                content += delta
                yield {"type": "delta", "delta": delta}
        except Exception as exc:  # noqa: BLE001
            log.warning("AI chat final summary after tools failed: %s", exc)
        yield {
            "type": "step",
            "id": gen_id,
            "kind": "generating",
            "label": "回复已生成" if content.strip() else "生成失败",
            "status": "done" if content.strip() else "error",
        }

    if not (content or "").strip():
        content = _PENDING_REPLY if pending_action else _EMPTY_REPLY
        async for delta_event in _emit_deltas(content):
            yield delta_event

    yield {
        "type": "final",
        "content": content,
        "tool_calls": last_tool_calls,
        "pending_action": pending_action,
    }


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

    async def delete_session(
        self,
        db: AsyncSession,
        *,
        user_id: int | None,
        session_id: int,
    ) -> None:
        sess = await db.get(AiGuardChatSession, session_id)
        self._ensure_session_owner(sess, user_id)
        await session_store.delete_session(db, session_id)

    async def delete_all_sessions(self, db: AsyncSession, *, user_id: int | None) -> int:
        return await session_store.delete_all_sessions(db, user_id=user_id)

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
        try:
            client = LlmClient(cfg)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

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
                "content": "知识上下文：\n" + json.dumps(snapshot, ensure_ascii=False)[:_KNOWLEDGE_SNAPSHOT_MAX_CHARS],
            },
            *_history_to_messages(history),
        ]

        tool_calls = None
        pending_action = None
        try:
            content, tool_calls, pending_action = await _complete_with_tools(client, db, messages)
        except Exception as exc:  # noqa: BLE001
            log.exception("AI chat completion failed for session %s", session_id)
            content = f"抱歉，处理请求时出错：{format_llm_error(exc)}"
            tool_calls = None
            pending_action = None

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
        cfg = await load_runtime_config(db)
        if not cfg.enabled or not cfg.chat_enabled:
            raise ValueError("AI 聊天功能未启用")
        try:
            client = LlmClient(cfg)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        if session_id is None:
            sess = await session_store.create_session(db, user_id=user_id, title=message[:40])
            session_id = sess.id
        else:
            sess = await db.get(AiGuardChatSession, session_id)
            self._ensure_session_owner(sess, user_id)

        yield json.dumps({"type": "session", "session_id": session_id}, ensure_ascii=False)

        await session_store.add_message(db, session_id=session_id, role="user", content=message)
        history = await session_store.get_messages(db, session_id)
        snapshot = await build_knowledge_snapshot(db)

        messages = [
            {"role": "system", "content": CHAT_SYSTEM},
            {
                "role": "system",
                "content": "知识上下文：\n" + json.dumps(snapshot, ensure_ascii=False)[:_KNOWLEDGE_SNAPSHOT_MAX_CHARS],
            },
            *_history_to_messages(history),
        ]

        content = ""
        tool_calls = None
        pending_action = None

        try:
            async for event in _stream_complete_with_tools(client, db, messages):
                if event.get("type") == "final":
                    content = event.get("content") or content
                    tool_calls = event.get("tool_calls")
                    pending_action = event.get("pending_action")
                    continue
                if event.get("type") == "delta":
                    content += event.get("delta") or ""
                yield json.dumps(event, ensure_ascii=False, default=str)
        except Exception as exc:  # noqa: BLE001
            log.exception("AI chat stream failed for session %s", session_id)
            content = f"抱歉，处理请求时出错：{format_llm_error(exc)}"
            yield json.dumps({"type": "delta", "delta": content}, ensure_ascii=False)

        if not (content or "").strip():
            content = _PENDING_REPLY if pending_action else _EMPTY_REPLY
            async for delta_event in _emit_deltas(content):
                yield json.dumps(delta_event, ensure_ascii=False)

        msg_row = await session_store.add_message(
            db,
            session_id=session_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            pending_action=pending_action,
            action_status="pending" if pending_action else None,
        )
        yield json.dumps(
            {
                "type": "done",
                "message_id": msg_row.id,
                "pending_action": pending_action,
            },
            ensure_ascii=False,
            default=str,
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
                args = act.get("arguments", {})
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
