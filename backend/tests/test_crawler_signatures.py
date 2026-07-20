"""Tests for vendored crawler config export."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.crawler_signatures import get_crawler_detect_config
from app.services.crawler_vendored.match import invalidate_match_cache, is_crawler_ua
from app.services.crawler_vendored.store import save_bundle


@pytest.fixture(autouse=True)
def _install_vendored(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.crawler_vendored.store.settings.crawler_vendored_path", str(tmp_path))
    seed_dir = Path(__file__).resolve().parents[1] / "app" / "data" / "crawler_detect_seed"
    crawlers = json.loads((seed_dir / "Crawlers.json").read_text(encoding="utf-8"))
    exclusions = json.loads((seed_dir / "Exclusions.json").read_text(encoding="utf-8"))
    save_bundle(
        crawlers=crawlers,
        exclusions=exclusions,
        upstream_commit="test",
        source="test",
    )
    invalidate_match_cache()


def test_crawler_detect_config_exports_regex_bundle():
    cfg = get_crawler_detect_config()
    assert "patterns" in cfg
    assert "exclusions" in cfg
    assert len(cfg["patterns"]) > 1000
    assert len(cfg["exclusions"]) > 10


def test_crawler_detect_config_matches_python_detector():
    ua = "Mozilla/5.0 (compatible; Sosospider/2.0; +http://help.soso.com/webspider.htm)"
    is_crawler, name = is_crawler_ua(ua)
    assert is_crawler
    assert name == "Sosospider"

    cfg = get_crawler_detect_config()
    assert cfg["patterns"].startswith("(")
    assert "|" in cfg["patterns"]
