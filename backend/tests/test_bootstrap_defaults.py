"""Tests for built-in default policy definitions."""
import pytest

from app.services.bootstrap_defaults import (
    DEFAULT_BLACKLIST,
    DEFAULT_EXCEPTIONS,
    DEFAULT_IP_GROUPS,
    DEFAULT_RATE_LIMITS,
    DEFAULT_RULES,
    DEFAULT_WHITELIST,
    _normalize_conditions,
)
from app.services.bootstrap_bots import DEFAULT_BOTS
from app.services.bootstrap_bot_categories import DEFAULT_CATEGORIES
from app.services.ip_entry import normalize_entries


@pytest.mark.parametrize("spec", DEFAULT_RULES, ids=lambda s: s["name"])
def test_default_rules_validate(spec):
    cond = _normalize_conditions(spec["conditions"])
    assert cond["logic"] in ("and", "or")
    assert spec["mode"] in ("observe", "block", "captcha", "js_challenge", "slide_captcha")
    assert spec["name"]


@pytest.mark.parametrize("spec", DEFAULT_RATE_LIMITS, ids=lambda s: s["name"])
def test_default_rate_limits_validate(spec):
    if spec.get("conditions"):
        _normalize_conditions(spec["conditions"])
    assert spec["threshold"] > 0
    assert spec["window"] > 0
    assert spec["name"]


@pytest.mark.parametrize("spec", [*DEFAULT_BLACKLIST, *DEFAULT_WHITELIST], ids=lambda s: s["name"])
def test_default_lists_validate(spec):
    _normalize_conditions(spec["conditions"])
    assert spec["list_type"] in ("black", "white")


@pytest.mark.parametrize("spec", DEFAULT_EXCEPTIONS, ids=lambda s: s["name"])
def test_default_exceptions_validate(spec):
    _normalize_conditions(spec["conditions"])
    assert spec.get("scope") in (None, "all", "rules", "ratelimit")


@pytest.mark.parametrize("spec", DEFAULT_IP_GROUPS, ids=lambda s: s["name"])
def test_default_ip_groups_validate(spec):
    entries = normalize_entries(spec.get("entries") or [])
    assert entries


def test_catalog_sizes():
    assert len(DEFAULT_RULES) == 6
    assert len(DEFAULT_RATE_LIMITS) == 5
    assert len(DEFAULT_BLACKLIST) == 6
    assert len(DEFAULT_WHITELIST) == 1
    assert len(DEFAULT_EXCEPTIONS) == 1
    assert len(DEFAULT_IP_GROUPS) == 1
    assert len(DEFAULT_CATEGORIES) == 8
    assert len(DEFAULT_BOTS) == 63


def test_bot_categories_cover_bot_refs():
    known = {c["value"] for c in DEFAULT_CATEGORIES}
    for bot in DEFAULT_BOTS:
        for cat in bot.get("categories") or []:
            assert cat in known, f"{bot['name']} references missing category {cat}"


def test_regular_cc_thresholds():
    static = next(s for s in DEFAULT_RATE_LIMITS if s["name"] == "CC防护-静态文件[常规]")
    dynamic = next(s for s in DEFAULT_RATE_LIMITS if s["name"] == "CC防护-动态网页[常规]")
    assert static["threshold"] > dynamic["threshold"]
