"""Download and refresh vendored Crawler-Detect rules from upstream."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import rule_sync
from app.services.crawler_vendored.store import (
    UPSTREAM_BRANCH,
    UPSTREAM_REPO,
    has_local_bundle,
    install_seed_if_missing,
    is_auto_update_due,
    load_manifest,
    manifest_for_api,
    save_bundle,
)

log = logging.getLogger("waf.crawler_vendored.sync")

UPSTREAM_CRAWLERS_URL = (
    f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_BRANCH}/raw/Crawlers.json"
)
UPSTREAM_EXCLUSIONS_URL = (
    f"https://raw.githubusercontent.com/{UPSTREAM_REPO}/{UPSTREAM_BRANCH}/raw/Exclusions.json"
)
UPSTREAM_COMMIT_URL = f"https://api.github.com/repos/{UPSTREAM_REPO}/commits/{UPSTREAM_BRANCH}"

_sync_lock = asyncio.Lock()


async def _fetch_upstream_commit(client: httpx.AsyncClient) -> str | None:
    try:
        resp = await client.get(UPSTREAM_COMMIT_URL, headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        data = resp.json()
        sha = data.get("sha")
        return str(sha) if sha else None
    except Exception:  # noqa: BLE001
        log.warning("failed to fetch upstream commit metadata", exc_info=True)
        return None


async def _download_rules() -> tuple[list[str], list[str], str | None]:
    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        crawlers_resp, exclusions_resp = await asyncio.gather(
            client.get(UPSTREAM_CRAWLERS_URL),
            client.get(UPSTREAM_EXCLUSIONS_URL),
        )
        crawlers_resp.raise_for_status()
        exclusions_resp.raise_for_status()
        crawlers = crawlers_resp.json()
        exclusions = exclusions_resp.json()
        commit = await _fetch_upstream_commit(client)
    if not isinstance(crawlers, list) or not isinstance(exclusions, list):
        raise ValueError("upstream crawler rules payload is invalid")
    if not crawlers:
        raise ValueError("upstream crawler rules are empty")
    return crawlers, exclusions, commit


async def sync_from_upstream(
    db: AsyncSession,
    *,
    force: bool = False,
    source: str = "upstream",
) -> dict[str, Any]:
    async with _sync_lock:
        if not force:
            manifest = load_manifest()
            if manifest and not is_auto_update_due():
                return {
                    "updated": False,
                    "reason": "not_due",
                    "manifest": manifest_for_api(),
                }

        crawlers, exclusions, commit = await _download_rules()
        manifest = save_bundle(
            crawlers=crawlers,
            exclusions=exclusions,
            upstream_commit=commit,
            source=source,
        )
        from app.services.crawler_vendored.match import invalidate_match_cache

        invalidate_match_cache()
        await rule_sync.publish(db)
        log.info(
            "crawler vendored rules updated (%d crawlers, commit=%s)",
            len(crawlers),
            commit or "unknown",
        )
        return {
            "updated": True,
            "manifest": manifest_for_api(),
            "upstream_commit": manifest.get("upstream_commit"),
        }


async def ensure_vendored_rules(db: AsyncSession) -> None:
    install_seed_if_missing()
    from app.services.crawler_vendored.match import invalidate_match_cache

    invalidate_match_cache()
    if not has_local_bundle():
        await sync_from_upstream(db, force=True, source="bootstrap")
        return
    if is_auto_update_due():
        try:
            await sync_from_upstream(db, force=True, source="auto")
        except Exception:  # noqa: BLE001
            log.exception("scheduled crawler vendored sync failed; keeping existing bundle")


async def maybe_auto_sync(db: AsyncSession) -> None:
    if not has_local_bundle():
        await ensure_vendored_rules(db)
        return
    if not is_auto_update_due():
        return
    try:
        await sync_from_upstream(db, force=True, source="auto")
    except Exception:  # noqa: BLE001
        log.exception("background crawler vendored sync failed")
