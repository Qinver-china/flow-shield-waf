from app.services.logging.payload_slim import payload_for_storage, slim_payload


def test_slim_payload_strips_promoted_headers_and_legacy_keys():
    raw = {
        "client_ip": "203.0.113.1",
        "request": {"method": "GET", "url": "https://example.com/"},
        "rule": {"id": 1, "name": "test"},
        "cookie_raw": "a=1; b=2",
        "evaluated": [{"field": "http.body.raw", "value": "x"}],
        "headers": {
            "User-Agent": "bot",
            "Referer": "https://ref",
            "Cookie": "a=1",
            "Host": "example.com",
            "X-Forwarded-For": "203.0.113.1",
            "Accept": "text/html",
        },
        "cookies": {"a": "1", "b": "2"},
        "query": {"q": "test"},
        "client": {"ip": "203.0.113.1", "port": 54321},
    }
    out = slim_payload(raw)
    assert "client_ip" not in out
    assert "request" not in out
    assert "rule" not in out
    assert "cookie_raw" not in out
    assert "evaluated" not in out
    assert out["headers"] == {"Accept": "text/html"}
    assert out["cookies"] == {"a": "1", "b": "2"}
    assert out["query"] == {"q": "test"}
    assert out["client"] == {"port": 54321}


def test_payload_for_storage_drops_evaluated_and_legacy_nested_fields():
    entry = {
        "client_ip": "198.51.100.2",
        "payload": {
            "evaluated": [{"field": "geo.country", "value": "CN"}],
            "request": {"uri": "/api"},
            "headers": {"User-Agent": "ua", "X-Custom": "1"},
            "cookies": {"sid": "abc"},
        },
    }
    out = payload_for_storage(entry)
    assert "evaluated" not in out
    assert "request" not in out
    assert out["headers"] == {"X-Custom": "1"}
    assert out["cookies"] == {"sid": "abc"}


def test_payload_for_storage_fallback_from_top_level_keys():
    entry = {
        "headers": {"User-Agent": "ua", "Authorization": "Bearer x"},
        "cookies": {"k": "v"},
        "client": {"ip": "10.0.0.1", "port": 8080},
    }
    out = payload_for_storage(entry)
    assert out["headers"] == {"Authorization": "Bearer x"}
    assert out["client"] == {"port": 8080}
