"""Shared response envelope and pagination helpers."""
from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: Any = None


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data}


class Page(BaseModel):
    total: int
    items: list[Any]
    page: int
    page_size: int
