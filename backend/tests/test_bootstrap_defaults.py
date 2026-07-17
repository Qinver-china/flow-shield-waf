"""Tests for built-in default policy definitions."""
import pytest

from app.services.bootstrap_defaults import (
    BUILTIN_PREFIX,
    DEFAULT_RATE_LIMITS,
    DEFAULT_RULES,
    _normalize_conditions,
)


@pytest.mark.parametrize("spec", DEFAULT_RULES, ids=lambda s: s["name"])
def test_default_rules_validate(spec):
    cond = _normalize_conditions(spec["conditions"])
    assert cond["logic"] in ("and", "or")
    assert spec["mode"] in ("observe", "block", "captcha", "js_challenge", "slide_captcha")
    assert spec["name"].startswith(BUILTIN_PREFIX)


@pytest.mark.parametrize("spec", DEFAULT_RATE_LIMITS, ids=lambda s: s["name"])
def test_default_rate_limits_validate(spec):
    if spec.get("conditions"):
        _normalize_conditions(spec["conditions"])
    assert spec["threshold"] > 0
    assert spec["window"] > 0
    assert spec["name"].startswith(BUILTIN_PREFIX)


def test_static_higher_than_dynamic_threshold():
    static = next(
        s for s in DEFAULT_RATE_LIMITS
        if "静态资源" in s["name"] and "单 URI" not in s["name"]
    )
    dynamic = next(s for s in DEFAULT_RATE_LIMITS if "动态页面" in s["name"])
    assert static["threshold"] > dynamic["threshold"]


def test_catalog_sizes():
    assert len(DEFAULT_RULES) >= 10
    assert len(DEFAULT_RATE_LIMITS) >= 6
