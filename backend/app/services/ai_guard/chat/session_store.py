"""Chat session persistence."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_guard import AiGuardChatMessage, AiGuardChatSession


async def create_session(db: AsyncSession, *, user_id: int | None, title: str = "新对话") -> AiGuardChatSession:
    row = AiGuardChatSession(title=title, user_id=user_id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def list_sessions(db: AsyncSession, *, user_id: int | None, limit: int = 30) -> list[AiGuardChatSession]:
    q = select(AiGuardChatSession).order_by(AiGuardChatSession.id.desc()).limit(limit)
    if user_id is not None:
        q = q.where(AiGuardChatSession.user_id == user_id)
    return list((await db.execute(q)).scalars().all())


async def get_messages(db: AsyncSession, session_id: int) -> list[AiGuardChatMessage]:
    rows = (
        await db.execute(
            select(AiGuardChatMessage)
            .where(AiGuardChatMessage.session_id == session_id)
            .order_by(AiGuardChatMessage.id.asc())
        )
    ).scalars().all()
    return list(rows)


async def add_message(
    db: AsyncSession,
    *,
    session_id: int,
    role: str,
    content: str,
    tool_calls: list | None = None,
    pending_action: dict | None = None,
    action_status: str | None = None,
) -> AiGuardChatMessage:
    row = AiGuardChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        pending_action=pending_action,
        action_status=action_status,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_message_action(
    db: AsyncSession, message_id: int, *, action_status: str
) -> AiGuardChatMessage | None:
    row = await db.get(AiGuardChatMessage, message_id)
    if row is None:
        return None
    row.action_status = action_status
    await db.commit()
    await db.refresh(row)
    return row


async def delete_session(db: AsyncSession, session_id: int) -> None:
    await db.execute(delete(AiGuardChatMessage).where(AiGuardChatMessage.session_id == session_id))
    row = await db.get(AiGuardChatSession, session_id)
    if row is not None:
        await db.delete(row)
    await db.commit()


async def delete_all_sessions(db: AsyncSession, *, user_id: int | None) -> int:
    q = select(AiGuardChatSession.id)
    if user_id is not None:
        q = q.where(AiGuardChatSession.user_id == user_id)
    session_ids = [int(row[0]) for row in (await db.execute(q)).all()]
    if not session_ids:
        return 0
    await db.execute(delete(AiGuardChatMessage).where(AiGuardChatMessage.session_id.in_(session_ids)))
    await db.execute(delete(AiGuardChatSession).where(AiGuardChatSession.id.in_(session_ids)))
    await db.commit()
    return len(session_ids)
