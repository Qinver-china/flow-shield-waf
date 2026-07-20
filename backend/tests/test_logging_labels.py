"""Tests for log statistics label formatting."""
from app.services.logging.labels import (
    format_dimension_label,
    format_geo_isp,
    format_rule_stats_label,
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
