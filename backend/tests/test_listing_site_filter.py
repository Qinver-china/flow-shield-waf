"""Listing site filter tests."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.api.listing import apply_site_filter
from app.models.base import Base
from app.models.rule import Rule


def test_apply_site_filter_single_site_id():
    stmt = select(Rule)
    filtered = apply_site_filter(stmt, Rule.site_ids, 3)
    compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert "json_each" in compiled
    assert "site_ids" in compiled


def test_apply_site_filter_multiple_site_ids():
    stmt = select(Rule)
    filtered = apply_site_filter(stmt, Rule.site_ids, [2, 5])
    compiled = str(filtered.compile(compile_kwargs={"literal_binds": True}))
    assert compiled.count("json_each") >= 2


def test_site_scope_filter_matches_sqlite_data():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[Rule.__table__])
    with Session(engine) as session:
        session.add(
            Rule(
                name="global",
                site_ids=None,
                priority=100,
                mode="block",
                enabled=True,
                conditions={"logic": "and", "conditions": []},
            )
        )
        session.add(
            Rule(
                name="site-2",
                site_ids=[2, 5],
                priority=100,
                mode="block",
                enabled=True,
                conditions={"logic": "and", "conditions": []},
            )
        )
        session.commit()
        stmt = apply_site_filter(select(Rule), Rule.site_ids, 2)
        names = [r.name for r in session.scalars(stmt).all()]
    assert names == ["site-2"]
