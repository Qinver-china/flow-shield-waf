"""Tests for rule stats label resolution helpers."""
from app.services.logging.query_clickhouse import (
    _dimension_groups_inner_sql,
    _paginate,
    _pick_rule_name,
    _pick_site_display,
    _rule_ref,
)


def test_rule_ref_normalizes_source():
    assert _rule_ref("ratelimit", 9) == ("ratelimit", 9)
    assert _rule_ref(None, 9) == ("unknown", 9)


def test_pick_rule_name_prefers_db_label():
    label_map = {("ratelimit", 9): "动态网页-JS"}
    assert _pick_rule_name("ratelimit", 9, "旧名称", label_map) == "动态网页-JS"


def test_pick_rule_name_falls_back_to_snapshot():
    assert _pick_rule_name("ratelimit", 9, "历史名称", {}) == "历史名称"


def test_pick_rule_name_generic_when_missing():
    assert _pick_rule_name("rule", 16, None, {}) == "规则 #16"


def test_pick_site_display_prefers_db_domain():
    label_map = {1: ("本地zibll", "new.example.com")}
    name, domain = _pick_site_display(1, "old.example.com", label_map)
    assert name == "本地zibll"
    assert domain == "new.example.com"


def test_pick_site_display_falls_back_to_snapshot():
    name, domain = _pick_site_display(2, "legacy.example.com", {})
    assert name is None
    assert domain == "legacy.example.com"


def test_paginate_clause():
    page, page_size, clause = _paginate(2, 20)
    assert page == 2
    assert page_size == 20
    assert clause == "LIMIT 20 OFFSET 20"


def test_dimension_groups_inner_sql_for_site_id():
    sql = _dimension_groups_inner_sql("site_id", "ts >= {start:DateTime}")
    assert "GROUP BY site_id" in sql
    assert "domain" not in sql
