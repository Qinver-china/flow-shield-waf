"""Tests for vendored Crawler-Detect compile and match."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.crawler_vendored.compile import compile_bundle, match_crawler_name
from app.services.crawler_vendored.match import is_crawler_ua, invalidate_match_cache
from app.services.crawler_vendored.store import save_bundle


@pytest.fixture
def vendored_bundle(tmp_path, monkeypatch):
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
    return compile_bundle(crawlers, exclusions)


def test_compile_bundle_shape(vendored_bundle):
    assert vendored_bundle["patterns"].startswith("(")
    assert "|" in vendored_bundle["patterns"]
    assert vendored_bundle["exclusions"].startswith("(")


def test_match_crawler_name_sosospider(vendored_bundle):
    ua = "Mozilla/5.0 (compatible; Sosospider/2.0; +http://help.soso.com/webspider.htm)"
    name = match_crawler_name(
        ua,
        patterns=vendored_bundle["patterns"],
        exclusions=vendored_bundle["exclusions"],
    )
    assert name == "Sosospider"


def test_is_crawler_ua_wrapper(vendored_bundle):
    ua = "Mozilla/5.0 (compatible; Sosospider/2.0; +http://help.soso.com/webspider.htm)"
    is_crawler, name = is_crawler_ua(ua)
    assert is_crawler
    assert name == "Sosospider"
