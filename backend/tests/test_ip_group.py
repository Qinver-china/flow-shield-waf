"""Tests for IP group entries and condition operators."""
import pytest

from app.fields import validate_condition
from app.services.ip_entry import normalize_entries, normalize_entry, parse_lines


def test_normalize_ipv4():
    assert normalize_entry("1.2.3.4") == "1.2.3.4"


def test_normalize_cidr():
    assert normalize_entry("10.0.0.0/8") == "10.0.0.0/8"


def test_normalize_invalid_ip():
    with pytest.raises(ValueError):
        normalize_entry("not-an-ip")


def test_parse_lines_skips_comments_and_blank():
    text = "1.1.1.1\n\n# comment\n2.2.2.2\n"
    assert parse_lines(text) == ["1.1.1.1", "2.2.2.2"]


def test_normalize_entries_dedupes():
    assert normalize_entries(["1.1.1.1", "1.1.1.1", "2.2.2.2"]) == ["1.1.1.1", "2.2.2.2"]


def test_ip_group_condition_ok():
    cond = validate_condition({
        "field": "ip.src",
        "op": "in_ip_group",
        "value": [1, 2],
    })
    assert cond["conditions"][0]["value"] == [1, 2]


def test_ip_group_condition_requires_ids():
    with pytest.raises(ValueError):
        validate_condition({"field": "ip.src", "op": "in_ip_group", "value": []})
