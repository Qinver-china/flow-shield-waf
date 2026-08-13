"""Idempotently insert a same-server panel connection. Used by install.sh.

Does not go through the login API — the admin password in `.env` may have changed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import PanelConnection
from app.schemas.panel_connection import PROVIDERS, normalize_panel_url

PROVIDERS_HELP = "baota | onepanel"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(f"FSWAF_{name}") or os.environ.get(name) or default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def _parse_extra(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("PANEL_EXTRA 必须是 JSON 对象")
    return data


async def upsert_local_panel(
    *,
    provider: str,
    name: str,
    panel_url: str,
    api_key: str = "",
    same_server: bool = True,
    verify_tls: bool = False,
    enabled: bool = True,
    remark: str | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[str, PanelConnection]:
    """Insert a same-server account. Skip if one already exists for this provider."""
    if provider not in PROVIDERS:
        raise ValueError(f"不支持的面板类型：{provider}（{PROVIDERS_HELP}）")
    panel_url = normalize_panel_url(panel_url)
    extra = extra or {}

    async with SessionLocal() as db:
        existing = (
            await db.execute(
                select(PanelConnection).where(
                    PanelConnection.provider == provider,
                    PanelConnection.same_server.is_(True),
                )
            )
        ).scalars().first()
        if existing is not None:
            return "skipped", existing

        row = PanelConnection(
            name=name.strip() or ("本机宝塔" if provider == "baota" else "本机 1Panel"),
            provider=provider,
            panel_url=panel_url,
            api_key=api_key or "",
            same_server=same_server,
            verify_tls=verify_tls,
            enabled=enabled,
            remark=remark,
            extra=extra,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return "created", row


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="写入本机面板账号（幂等）")
    parser.add_argument("--provider", default=_env("PANEL_PROVIDER"))
    parser.add_argument("--name", default=_env("PANEL_NAME"))
    parser.add_argument("--panel-url", default=_env("PANEL_URL"))
    parser.add_argument("--api-key", default=_env("PANEL_API_KEY"))
    parser.add_argument(
        "--same-server",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("PANEL_SAME_SERVER", True),
    )
    parser.add_argument(
        "--verify-tls",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("PANEL_VERIFY_TLS", False),
    )
    parser.add_argument(
        "--enabled",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("PANEL_ENABLED", True),
    )
    parser.add_argument("--remark", default=_env("PANEL_REMARK") or None)
    parser.add_argument("--extra", default=_env("PANEL_EXTRA"))
    return parser


async def _async_main(args: argparse.Namespace) -> int:
    provider = (args.provider or "").strip()
    name = (args.name or "").strip()
    panel_url = (args.panel_url or "").strip()
    if not provider or not panel_url:
        print("需要 --provider 与 --panel-url（或 PANEL_PROVIDER / PANEL_URL）", file=sys.stderr)
        return 2
    if not name:
        name = "本机宝塔" if provider == "baota" else "本机 1Panel"
    try:
        extra = _parse_extra(args.extra or "")
        status, row = await upsert_local_panel(
            provider=provider,
            name=name,
            panel_url=panel_url,
            api_key=args.api_key or "",
            same_server=bool(args.same_server),
            verify_tls=bool(args.verify_tls),
            enabled=bool(args.enabled),
            remark=args.remark,
            extra=extra,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"error {exc}", file=sys.stderr)
        return 1

    missing = ""
    if not (row.api_key or "").strip():
        missing = " missing_api_key"
    print(f"{status} {row.provider} name={row.name} id={row.id}{missing}")
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
