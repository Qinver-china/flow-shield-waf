"""Tests for IP group entries and condition operators."""
import pytest

from app.fields import validate_condition
from app.services.ip_entry import normalize_entries, normalize_entry, parse_lines


def test_normalize_ipv4():
    assert normalize_entry("1.2.3.4") == "1.2.3.4"


def test_normalize_cidr():
    assert normalize_entry("10.0.0.0/8") == "10.0.0.0/8"


def test_normalize_ipv6():
    assert normalize_entry("2001:0db8::1") == "2001:db8::1"
    assert normalize_entry("[2001:db8::1]") == "2001:db8::1"


def test_normalize_ipv6_cidr():
    assert normalize_entry("2001:db8::/32") == "2001:db8::/32"
    assert normalize_entry("2001:db8::1/32") == "2001:db8::/32"
    assert normalize_entry("[2001:db8::]/32") == "2001:db8::/32"


def test_normalize_ipv4_mapped_ipv6():
    assert normalize_entry("::ffff:1.2.3.4") == "1.2.3.4"


def test_normalize_rejects_ipv6_zone():
    with pytest.raises(ValueError):
        normalize_entry("fe80::1%eth0")


def test_normalize_invalid_ip():
    with pytest.raises(ValueError):
        normalize_entry("not-an-ip")
    with pytest.raises(ValueError):
        normalize_entry("2001:db8::/129")


def test_parse_lines_skips_comments_and_blank():
    text = "1.1.1.1\n\n# comment\n2.2.2.2\n"
    assert parse_lines(text) == ["1.1.1.1", "2.2.2.2"]


def test_normalize_entries_dedupes():
    assert normalize_entries(["1.1.1.1", "1.1.1.1", "2.2.2.2"]) == ["1.1.1.1", "2.2.2.2"]


def test_normalize_entries_dedupes_ipv6_forms():
    assert normalize_entries(["2001:db8:0:0:0:0:0:1", "2001:db8::1"]) == ["2001:db8::1"]


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
