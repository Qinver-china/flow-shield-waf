"""Tests for CrawlerDetect config export."""
from __future__ import annotations

from app.services.crawler_signatures import get_crawler_detect_config
from app.services.logging.crawler_detect import is_crawler_ua


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
