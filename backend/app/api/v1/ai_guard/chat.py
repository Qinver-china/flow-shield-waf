import json

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
    rows = await chat_service.get_session_messages(db, user_id=user.id, session_id=session_id)
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
                async for chunk in chat_service.stream_chat(
                    db,
                    user_id=user.id,
                    session_id=body.session_id,
                    message=body.message,
                ):
                    yield f"data: {chunk}\n\n"
            except ValueError as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
            except Exception as exc:  # noqa: BLE001
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


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
