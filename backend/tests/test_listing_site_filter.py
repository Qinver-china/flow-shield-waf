"""Listing site filter tests."""

from sqlalchemy import select

from app.api.listing import apply_site_filter
from app.models.rule import Rule


def test_apply_site_filter_single_site_id():
    stmt = select(Rule)
    filtered = apply_site_filter(stmt, Rule.site_ids, 3)
    compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert "site_ids" in compiled


def test_apply_site_filter_multiple_site_ids():
    stmt = select(Rule)
    filtered = apply_site_filter(stmt, Rule.site_ids, [2, 5])
    compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert compiled.count("JSON_CONTAINS") >= 2
