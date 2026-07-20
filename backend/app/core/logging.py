"""Structured (JSON) application logging."""
from __future__ import annotations

import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False)


def _resolve_level(level: str | int | None) -> int:
    if level is None:
        from app.core.config import settings

        level = settings.log_level
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.WARNING)


def setup_logging(level: str | int | None = None) -> None:
    resolved = _resolve_level(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(resolved)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(resolved)
