"""AI Guard log query tool mapping tests."""

from app.services.ai_guard.log_query import build_log_query_from_tool_args


def test_build_log_query_from_hours_and_filters():
    q = build_log_query_from_tool_args(
        {
            "hours": 12,
            "site_id": 3,
            "blocked": True,
            "keyword": "union",
            "filters": [
                {"field": "uri_path", "op": "contains", "value": "/api"},
                {"field": "method", "op": "eq", "value": "POST"},
            ],
            "limit": 25,
        }
    )
    assert q.site_id == 3
    assert q.blocked is True
    assert q.keyword == "union"
    assert q.page_size == 25
    assert q.filters is not None
    assert '"uri_path"' in q.filters
    assert q.start is not None and q.end is not None


def test_build_log_query_caps_limit():
    q = build_log_query_from_tool_args({"limit": 500})
    assert q.page_size == 100
