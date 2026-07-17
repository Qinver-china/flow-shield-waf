from app.services.logging.enrich import enrich_entry


def test_enrich_entry_fills_xff_first_from_payload_headers():
    entry = {
        "uri": "/",
        "payload": {
            "headers": {
                "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            },
            "query": {"a": "1", "b": "2"},
        },
    }
    out = enrich_entry(entry)
    assert out["xff_first"] == "203.0.113.1"
    assert out["query_count"] == 2


def test_enrich_entry_keeps_existing_xff_first():
    entry = {
        "uri": "/",
        "xff_first": "198.51.100.2",
        "payload": {"headers": {"X-Forwarded-For": "203.0.113.1"}},
    }
    out = enrich_entry(entry)
    assert out["xff_first"] == "198.51.100.2"
