import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import SessionLocal, get_db
from app.models import User
from app.schemas.ai_guard import ChatRequest, ConfirmActionRequest
from app.schemas.common import ok
from app.services.ai_guard.chat import session_store
from app.services.ai_guard.chat.service import chat_service

router = APIRouter()

_SSE_KEEPALIVE_SEC = 15.0


async def _sse_with_keepalive(chunks: AsyncIterator[str]) -> AsyncIterator[str]:
    """Emit SSE comment keepalives while waiting for the next chunk."""
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def _producer() -> None:
        try:
            async for chunk in chunks:
                await queue.put(chunk)
        finally:
            await queue.put(None)

    task = asyncio.create_task(_producer())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=_SSE_KEEPALIVE_SEC)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield f"data: {item}\n\n"
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = await session_store.list_sessions(db, user_id=user.id)
    return ok([
        {"id": r.id, "title": r.title, "created_at": r.created_at}
        for r in rows
    ])


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    rows = await chat_service.get_session_messages(db, user_id=_user.id, session_id=session_id)
    return ok([
        {
            "id": r.id,
            "role": r.role,
            "content": r.content,
            "pending_action": r.pending_action,
            "action_status": r.action_status,
            "created_at": r.created_at,
        }
        for r in rows
    ])


@router.delete("/sessions")
async def clear_all_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    deleted = await chat_service.delete_all_sessions(db, user_id=user.id)
    return ok({"deleted": deleted})


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        await chat_service.delete_session(db, user_id=user.id, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ok(None)


@router.post("")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        result = await chat_service.chat(
            db,
            user_id=user.id,
            session_id=body.session_id,
            message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(result)


@router.post("/stream")
async def chat_stream(
    body: ChatRequest,
    user: User = Depends(get_current_user),
):
    async def event_gen():
        async with SessionLocal() as db:
            try:
                async for line in _sse_with_keepalive(
                    chat_service.stream_chat(
                        db,
                        user_id=user.id,
                        session_id=body.session_id,
                        message=body.message,
                    )
                ):
                    yield line
            except ValueError as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
            except Exception as exc:  # noqa: BLE001
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/actions/confirm")
async def confirm_action(
    body: ConfirmActionRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    try:
        result = await chat_service.confirm_action(
            db,
            user_id=_user.id,
            message_id=body.message_id,
            approved=body.approved,
            edited_payload=body.edited_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(result)
