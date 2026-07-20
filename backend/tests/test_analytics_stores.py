"""Unit tests for analytics JSON helpers."""

import json

from app.services.analytics.incident_store import _json_str, _parse_json


def test_json_str_serializes_dict():
    assert json.loads(_json_str({"a": 1})) == {"a": 1}


def test_parse_json_from_string():
    assert _parse_json('{"x": 2}', {}) == {"x": 2}


def test_parse_json_default_on_invalid():
    assert _parse_json("not-json", {"ok": True}) == {"ok": True}
