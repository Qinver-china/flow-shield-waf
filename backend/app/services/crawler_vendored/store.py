"""Filesystem store for vendored Crawler-Detect rules."""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.crawler_vendored.compile import compile_bundle

log = logging.getLogger("waf.crawler_vendored.store")

UPSTREAM_REPO = "JayBizzle/Crawler-Detect"
UPSTREAM_BRANCH = "master"
SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "crawler_detect_seed"

MANIFEST_FILE = "manifest.json"
CRAWLERS_FILE = "Crawlers.json"
EXCLUSIONS_FILE = "Exclusions.json"
COMPILED_FILE = "compiled.json"


def vendored_dir() -> Path:
    return Path(settings.crawler_vendored_dir)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _content_hash(crawlers: list[str], exclusions: list[str]) -> str:
    payload = json.dumps({"crawlers": crawlers, "exclusions": exclusions}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def seed_dir() -> Path:
    return SEED_DIR


def has_local_bundle() -> bool:
    root = vendored_dir()
    return (root / COMPILED_FILE).is_file() and (root / MANIFEST_FILE).is_file()


def load_manifest() -> dict[str, Any] | None:
    path = vendored_dir() / MANIFEST_FILE
    if not path.is_file():
        return None
    return _read_json(path)


def load_compiled_config() -> dict[str, str]:
    path = vendored_dir() / COMPILED_FILE
    if not path.is_file():
        return {"patterns": "", "exclusions": ""}
    data = _read_json(path)
    return {
        "patterns": str(data.get("patterns") or ""),
        "exclusions": str(data.get("exclusions") or ""),
    }


def install_seed_if_missing() -> bool:
    root = vendored_dir()
    if has_local_bundle():
        return False
    if not SEED_DIR.is_dir():
        log.warning("crawler vendored seed missing at %s", SEED_DIR)
        return False
    root.mkdir(parents=True, exist_ok=True)
    for name in (CRAWLERS_FILE, EXCLUSIONS_FILE):
        shutil.copy2(SEED_DIR / name, root / name)
    crawlers = _read_json(root / CRAWLERS_FILE)
    exclusions = _read_json(root / EXCLUSIONS_FILE)
    if not isinstance(crawlers, list) or not isinstance(exclusions, list):
        raise ValueError("invalid crawler vendored seed JSON")
    save_bundle(
        crawlers=crawlers,
        exclusions=exclusions,
        upstream_commit=None,
        source="seed",
    )
    log.info("installed crawler vendored seed (%d crawlers)", len(crawlers))
    return True


def save_bundle(
    *,
    crawlers: list[str],
    exclusions: list[str],
    upstream_commit: str | None,
    source: str,
) -> dict[str, Any]:
    root = vendored_dir()
    root.mkdir(parents=True, exist_ok=True)
    _write_json(root / CRAWLERS_FILE, crawlers)
    _write_json(root / EXCLUSIONS_FILE, exclusions)
    compiled = compile_bundle(crawlers, exclusions)
    _write_json(root / COMPILED_FILE, compiled)

    now = datetime.now(timezone.utc)
    auto_days = max(1, settings.crawler_vendored_auto_update_days)
    manifest = {
        "upstream_repo": UPSTREAM_REPO,
        "upstream_branch": UPSTREAM_BRANCH,
        "upstream_commit": upstream_commit,
        "crawlers_count": len(crawlers),
        "exclusions_count": len(exclusions),
        "content_hash": _content_hash(crawlers, exclusions),
        "updated_at": now.isoformat(),
        "next_auto_update_at": (now + timedelta(days=auto_days)).isoformat(),
        "source": source,
    }
    _write_json(root / MANIFEST_FILE, manifest)
    try:
        from app.services.crawler_vendored.match import invalidate_match_cache

        invalidate_match_cache()
    except Exception:  # noqa: BLE001
        pass
    return manifest


def manifest_for_api() -> dict[str, Any]:
    manifest = load_manifest()
    if not manifest:
        return {
            "installed": False,
            "upstream_repo": UPSTREAM_REPO,
            "upstream_branch": UPSTREAM_BRANCH,
            "auto_update_days": settings.crawler_vendored_auto_update_days,
        }
    return {
        "installed": True,
        "upstream_repo": manifest.get("upstream_repo", UPSTREAM_REPO),
        "upstream_branch": manifest.get("upstream_branch", UPSTREAM_BRANCH),
        "upstream_commit": manifest.get("upstream_commit"),
        "crawlers_count": manifest.get("crawlers_count", 0),
        "exclusions_count": manifest.get("exclusions_count", 0),
        "updated_at": manifest.get("updated_at"),
        "next_auto_update_at": manifest.get("next_auto_update_at"),
        "source": manifest.get("source"),
        "auto_update_days": settings.crawler_vendored_auto_update_days,
    }


def is_auto_update_due() -> bool:
    manifest = load_manifest()
    if not manifest:
        return True
    raw = manifest.get("next_auto_update_at")
    if not raw:
        return True
    try:
        due_at = datetime.fromisoformat(str(raw))
    except ValueError:
        return True
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= due_at
