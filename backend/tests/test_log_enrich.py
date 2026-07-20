from pathlib import Path
import json

import pytest

from app.services.bot_identify import (
    identify_bot,
    is_bot_ua_heuristic,
    match_ua_pattern,
    resolve_bot_dimensions,
)
from app.services.logging.enrich import enrich_entry
from app.services.logging.ua_parse import parse_client_ua


@pytest.fixture(autouse=True)
def _install_vendored_crawlers(tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.crawler_vendored.store.settings.crawler_vendored_path", str(tmp_path))
    seed_dir = Path(__file__).resolve().parents[1] / "app" / "data" / "crawler_detect_seed"
    if not seed_dir.is_dir():
        return
    from app.services.crawler_vendored.match import invalidate_match_cache
    from app.services.crawler_vendored.store import save_bundle

    crawlers = json.loads((seed_dir / "Crawlers.json").read_text(encoding="utf-8"))
    exclusions = json.loads((seed_dir / "Exclusions.json").read_text(encoding="utf-8"))
    save_bundle(
        crawlers=crawlers,
        exclusions=exclusions,
        upstream_commit="test",
        source="test",
    )
    invalidate_match_cache()


def test_enrich_entry_normalizes_request_uri(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    out = enrich_entry({
        "request_uri": "/api?x=1",
        "uri_path": "/api",
        "query_count": 3,
    })
    assert out["request_uri"] == "/api?x=1"
    assert "uri" not in out
    assert out["query_count"] == 3


def test_enrich_entry_migrates_legacy_uri_key(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    out = enrich_entry({"uri": "/legacy?a=1"})
    assert out["request_uri"] == "/legacy?a=1"
    assert "uri" not in out
    assert out["uri_path"] == "/legacy"


def test_enrich_entry_fills_xff_first_from_payload_headers(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    entry = {
        "uri": "/",
        "payload": {
            "headers": {
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            },
            "query": {"a": "1", "b": "2"},
        },
    }
    out = enrich_entry(entry)
    assert out["xff_first"] == "203.0.113.1"
    assert out["query_count"] == 2


def test_enrich_entry_keeps_existing_xff_first(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    entry = {
        "uri": "/",
        "xff_first": "198.51.100.2",
        "payload": {"headers": {"X-Forwarded-For": "203.0.113.1"}},
    }
    out = enrich_entry(entry)
    assert out["xff_first"] == "198.51.100.2"


def test_match_ua_pattern_substring():
    assert match_ua_pattern("Mozilla/5.0 Googlebot/2.1", "Googlebot")


def test_match_ua_pattern_regex():
    assert match_ua_pattern("curl/8.0", "/curl/")


def test_identify_bot_from_catalog():
    bots = [
        {
            "name": "Googlebot",
            "category": "search_engine",
            "enabled": True,
            "ua_patterns": ["Googlebot"],
            "site_ids": None,
        }
    ]
    match = identify_bot("Mozilla/5.0 (compatible; Googlebot/2.1)", 1, bots)
    assert match == {"name": "Googlebot", "category": "search_engine"}


def test_parse_client_ua_chrome_macos():
    ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    family, os_name, browser = parse_client_ua(ua)
    assert family == "browser"
    assert os_name == "macOS"
    assert browser == "Chrome"


def test_parse_client_ua_bot():
    ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
    family, os_name, browser = parse_client_ua(ua)
    assert family == "bot"
    assert browser is None


def test_is_bot_ua_heuristic():
    assert is_bot_ua_heuristic("SomeCrawler/1.0 spider")


def test_enrich_entry_fills_bot_and_ua_dimensions(monkeypatch):
    bots = [
        {
            "name": "Googlebot",
            "category": "search_engine",
            "enabled": True,
            "ua_patterns": ["Googlebot"],
        }
    ]
    monkeypatch.setattr(
        "app.services.logging.enrich.get_bots",
        lambda: bots,
    )
    entry = {
        "uri": "/",
        "ua": "Mozilla/5.0 (compatible; Googlebot/2.1)",
        "site_id": 1,
    }
    out = enrich_entry(entry)
    assert out["bot_name"] == "Googlebot"
    assert out["bot_category"] == "search_engine"
    assert out["ua_family"] == "bot"
    assert out["ua_browser"] is None


def test_enrich_entry_crawlerdetect_fallback(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    monkeypatch.setattr("app.services.logging.enrich.get_category_values", lambda: {"other"})
    ua = "Mozilla/5.0 (compatible; Sosospider/2.0; +http://help.soso.com/webspider.htm)"
    out = enrich_entry({"uri": "/", "ua": ua})
    assert out["ua_family"] == "bot"
    assert out["bot_name"]
    assert out["bot_category"] == "other"
    assert out["ua_browser"] is None


def test_enrich_entry_trusts_engine_bot_dimensions(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    out = enrich_entry({
        "uri": "/",
        "ua": "Mozilla/5.0 (compatible; Googlebot/2.1)",
        "ua_family": "bot",
        "ua_os": "Linux",
        "bot_name": "Googlebot",
        "bot_category": "search_engine",
    })
    assert out["bot_name"] == "Googlebot"
    assert out["bot_category"] == "search_engine"
    assert out["ua_family"] == "bot"
    assert out["ua_browser"] is None


def test_resolve_bot_dimensions_unknown_crawler():
    name, category = resolve_bot_dimensions(
        "Mozilla/5.0 (compatible; Sosospider/2.0)",
        1,
        [],
        {"other", "search_engine"},
    )
    assert category == "other"


def test_resolve_bot_dimensions_invalid_profile_category():
    bots = [
        {
            "name": "LegacyBot",
            "category": "deleted_category",
            "enabled": True,
            "ua_patterns": ["LegacyBot"],
        }
    ]
    name, category = resolve_bot_dimensions(
        "LegacyBot/1.0",
        1,
        bots,
        {"other", "search_engine"},
    )
    assert name == "LegacyBot"
    assert category == "other"


def test_enrich_entry_clears_bot_when_no_catalog_match(monkeypatch):
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: [])
    entry = {
        "uri": "/",
        "ua": "Mozilla/5.0 Chrome/120.0.0.0",
        "bot_name": "stale-from-engine",
        "bot_category": "other",
    }
    out = enrich_entry(entry)
    assert out["bot_name"] is None
    assert out["bot_category"] is None
    assert out["ua_family"] == "browser"
    assert out["ua_browser"] == "Chrome"


def test_enrich_entries_matches_single_enrich(monkeypatch):
    bots = [
        {
            "name": "Googlebot",
            "category": "search_engine",
            "enabled": True,
            "ua_patterns": ["Googlebot"],
        }
    ]
    monkeypatch.setattr("app.services.logging.enrich.get_bots", lambda: bots)
    monkeypatch.setattr("app.services.logging.enrich.get_category_values", lambda: set())
    entries = [
        {"uri": "/", "ua": "Mozilla/5.0 (compatible; Googlebot/2.1)", "site_id": 1},
        {"uri": "/api", "ua": "Mozilla/5.0 Chrome/120.0.0.0"},
    ]
    from app.services.logging.enrich import enrich_entries

    batch = enrich_entries(entries)
    assert len(batch) == 2
    assert batch[0]["bot_name"] == "Googlebot"
    assert batch[1]["ua_family"] == "browser"
    for entry, enriched in zip(entries, batch):
        assert enrich_entry(entry) == enriched
