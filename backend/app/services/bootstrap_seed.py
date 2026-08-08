"""Load built-in seed catalog from packaged JSON."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parents[1] / "data" / "builtin_seed.json"


@lru_cache(maxsize=1)
def load_builtin_seed() -> dict[str, list[dict[str, Any]]]:
    raw = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    data = raw.get("data")
    if not isinstance(data, dict):
        raise ValueError(f"invalid builtin seed at {SEED_PATH}")
    return data


def seed_section(name: str) -> list[dict[str, Any]]:
    items = load_builtin_seed().get(name) or []
    if not isinstance(items, list):
        raise ValueError(f"builtin seed section {name!r} must be a list")
    return items
