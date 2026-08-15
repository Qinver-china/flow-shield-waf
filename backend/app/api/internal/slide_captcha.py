"""Slide captcha endpoints for the OpenResty engine."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.services.slide_captcha import SlideCaptchaService

router = APIRouter(prefix="/internal/waf/slide-captcha", tags=["internal"])


def _ensure_local(request: Request) -> None:
    """Allow loopback TCP and Unix-socket peers (uvicorn sets client=None on UDS)."""
    if request.client is None:
        return
    host = request.client.host or ""
    if host in {"127.0.0.1", "::1", ""}:
        return
    raise HTTPException(status_code=403, detail="forbidden")


@router.get("/issue")
async def issue_slide_captcha(request: Request):
    _ensure_local(request)
    try:
        data = await SlideCaptchaService.issue()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"code": 0, "message": "ok", "data": data}


class SlideVerifyIn(BaseModel):
    captcha_key: str = Field(min_length=8, max_length=64)
    x: int = Field(ge=0, le=4096)
    y: int = Field(ge=0, le=4096)

    @field_validator("x", "y", mode="before")
    @classmethod
    def _coerce_xy(cls, value: object) -> object:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float, str)):
            try:
                return int(float(value))
            except (TypeError, ValueError):
                return value
        return value


@router.post("/verify")
async def verify_slide_captcha(body: SlideVerifyIn, request: Request):
    _ensure_local(request)
    ok = await SlideCaptchaService.verify(body.captcha_key, body.x, body.y)
    if not ok:
        raise HTTPException(status_code=400, detail="verification failed")
    return {"code": 0, "message": "ok", "data": {"verified": True}}
