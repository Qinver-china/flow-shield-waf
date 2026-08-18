"""Tests for log list query filters."""
from datetime import datetime

from app.schemas.log import LogQuery
from app.services.logging.query_clickhouse import _where_clause


def test_where_clause_supports_extended_filters():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 2, 0, 0, 0)
    q = LogQuery(
        uri_path="/api/test",
        scheme="https",
        http_version="1.1",
        ip_is_private=True,
        xff_first="203.0.113.1",
        tcp_ip="198.51.100.1",
        geo_region="California",
        geo_city="Los Angeles",
        geo_isp="Example ISP",
        geo_asn=13335,
        ua="curl",
        ua_family="Bot",
        ua_os="Linux",
        ua_browser="curl",
        tls_version="TLSv1.3",
        rule_name="黑名单",
    )
    where, params = _where_clause(q, start, end)
    assert "waf_logs.uri_path = {uri_path:String}" in where
    assert "waf_logs.scheme = {scheme:String}" in where
    assert "waf_logs.http_version = {http_version:String}" in where
    assert "waf_logs.ip_is_private = {ip_is_private:UInt8}" in where
    assert "waf_logs.xff_first = {xff_first:String}" in where
    assert "waf_logs.tcp_ip = {tcp_ip:String}" in where
    assert "waf_logs.geo_region = {geo_region:String}" in where
    assert "waf_logs.geo_city = {geo_city:String}" in where
    assert "waf_logs.geo_isp = {geo_isp:String}" in where
    assert "waf_logs.geo_asn = {geo_asn:UInt32}" in where
    assert "positionCaseInsensitive(waf_logs.ua, {ua:String}) > 0" in where
    assert "waf_logs.ua_family = {ua_family:String}" in where
    assert "positionCaseInsensitive(waf_logs.rule_name, {rule_name:String}) > 0" in where
    assert params["uri_path"] == "/api/test"
    assert params["ip_is_private"] == 1
    assert params["tcp_ip"] == "198.51.100.1"
    assert params["geo_asn"] == 13335


def test_clickhouse_row_includes_tcp_ip():
    from app.services.logging.clickhouse_store import _COLUMNS, _row_from_enriched

    row = _row_from_enriched({
        "client_ip": "203.0.113.1",
        "tcp_ip": "198.51.100.1",
    })
    assert len(row) == len(_COLUMNS)
    assert row[_COLUMNS.index("client_ip")] == "203.0.113.1"
    assert row[_COLUMNS.index("tcp_ip")] == "198.51.100.1"


def test_where_clause_json_blocked_filter_uses_qualified_column():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 2, 0, 0, 0)
    q = LogQuery(filters='[{"field":"blocked","op":"eq","value":"true"}]')
    where, params = _where_clause(q, start, end)
    assert "waf_logs.blocked = {f_blocked_0:UInt8}" in where
    assert params["f_blocked_0"] == 1


def test_where_clause_json_cookie_filters():
    start = datetime(2026, 1, 1, 0, 0, 0)
    end = datetime(2026, 1, 2, 0, 0, 0)
    q = LogQuery(
        filters='[{"field":"cookie_name","op":"eq","value":"PHPSESSID"},'
        '{"field":"cookie","op":"contains","arg":"theme_mode","value":"dark"},'
        '{"field":"cookie_count_bucket","op":"eq","value":"6-20"}]'
    )
    where, params = _where_clause(q, start, end)
    assert "JSONHas(waf_logs.payload, 'cookies', {f_cookie_name_0:String})" in where
    assert "JSONExtractString(waf_logs.payload, 'cookies', {f_cookie_arg_10:String})" in where
    assert "positionCaseInsensitive(JSONExtractString(waf_logs.payload, 'cookies', {f_cookie_arg_10:String}), {f_cookie_val_10:String}) > 0" in where
    assert "multiIf(" in where and "cookie_count_bucket" not in where
    assert params["f_cookie_name_0"] == "PHPSESSID"
    assert params["f_cookie_arg_10"] == "theme_mode"
    assert params["f_cookie_val_10"] == "dark"
