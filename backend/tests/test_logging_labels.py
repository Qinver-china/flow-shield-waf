"""Tests for log statistics label formatting."""
from app.services.logging.labels import (
    format_dimension_label,
    format_geo_asn,
    format_geo_city,
    format_geo_isp,
    format_geo_region,
    format_rule_stats_label,
    geo_asn_field_options,
    geo_city_field_options,
    geo_region_field_options,
)


def test_format_rule_stats_label_with_source():
    assert format_rule_stats_label(
        rule_id=3,
        rule_name="全局IP黑名单",
        source="blacklist",
    ) == "[黑名单]全局IP黑名单 (#3)"


def test_format_rule_stats_label_without_source():
    assert format_rule_stats_label(rule_id=1, rule_name="测试规则", source=None) == "测试规则 (#1)"


def test_format_site_id_label_with_name_and_domain():
    assert (
        format_dimension_label(
            "site_id",
            "1",
            "站点 #1",
            site_name="本地zibll",
            site_domain="aaa.zibll.com",
        )
        == "本地zibll (aaa.zibll.com)"
    )


def test_format_geo_isp_common_carriers():
    assert format_geo_isp("China Telecom Guangdong") == "中国电信 (China Telecom Guangdong)"
    assert format_geo_isp("Amazon.com, Inc.") == "亚马逊 AWS (Amazon.com, Inc.)"
    assert format_geo_isp("CLOUDFLARENET") == "Cloudflare (CLOUDFLARENET)"
    assert format_geo_isp("Some Random ISP LLC") == "Some Random ISP LLC"


def test_format_dimension_label_geo_isp():
    assert (
        format_dimension_label("geo_isp", "Alibaba Cloud LLC", "Alibaba Cloud LLC")
        == "阿里云 (Alibaba Cloud LLC)"
    )


def test_format_geo_region_cn_and_us_codes():
    assert format_geo_region("GD", "CN") == "广东 (GD)"
    assert format_geo_region("VA", "US") == "弗吉尼亚 (VA)"
    assert format_geo_region("GD") == "广东 (GD)"
    assert format_geo_region("Guangdong") == "广东 (Guangdong)"
    assert format_geo_region("ZZ") == "ZZ"


def test_format_geo_city_common_names():
    assert format_geo_city("Beijing") == "北京 (Beijing)"
    assert format_geo_city("Los Angeles") == "洛杉矶 (Los Angeles)"
    assert format_geo_city("Xi'an") == "西安 (Xi'an)"
    assert format_geo_city("SomeTown") == "SomeTown"


def test_format_dimension_label_geo_region_and_city():
    assert format_dimension_label("geo_region", "GD", "GD") == "广东 (GD)"
    assert format_dimension_label("geo_city", "Shanghai", "Shanghai") == "上海 (Shanghai)"


def test_format_geo_asn_common():
    assert format_geo_asn(13335) == "Cloudflare (13335)"
    assert format_geo_asn("4134") == "中国电信 (4134)"
    assert format_geo_asn(999999) == "999999"
    assert format_geo_asn(None) == ""


def test_format_dimension_label_geo_asn():
    assert format_dimension_label("geo_asn", "16509", "16509") == "亚马逊 AWS (16509)"


def test_geo_field_options_for_rule_editor():
    regions = {item["value"] for item in geo_region_field_options()}
    assert "GD" in regions
    assert "VA" in regions
    cities = {item["value"] for item in geo_city_field_options()}
    assert "Beijing" in cities
    assert "Los Angeles" in cities
    asns = {item["value"] for item in geo_asn_field_options()}
    assert "16509" in asns
    assert any(item["label"].startswith("亚马逊 AWS") for item in geo_asn_field_options())
