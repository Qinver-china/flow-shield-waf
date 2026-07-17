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
        geo_region="California",
        geo_city="Los Angeles",
        geo_isp="Example ISP",
        geo_ip_type="datacenter",
        geo_asn=13335,
        ua="curl",
        ua_family="Bot",
        ua_os="Linux",
        ua_browser="curl",
        tls_version="TLSv1.3",
        rule_name="黑名单",
    )
    where, params = _where_clause(q, start, end)
    assert "uri_path = {uri_path:String}" in where
    assert "scheme = {scheme:String}" in where
    assert "http_version = {http_version:String}" in where
    assert "ip_is_private = {ip_is_private:UInt8}" in where
    assert "xff_first = {xff_first:String}" in where
    assert "geo_region = {geo_region:String}" in where
    assert "geo_city = {geo_city:String}" in where
    assert "geo_isp = {geo_isp:String}" in where
    assert "geo_ip_type = {geo_ip_type:String}" in where
    assert "geo_asn = {geo_asn:UInt32}" in where
    assert "positionCaseInsensitive(ua, {ua:String}) > 0" in where
    assert "ua_family = {ua_family:String}" in where
    assert "positionCaseInsensitive(rule_name, {rule_name:String}) > 0" in where
    assert params["uri_path"] == "/api/test"
    assert params["ip_is_private"] == 1
    assert params["geo_asn"] == 13335
