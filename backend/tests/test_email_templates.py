"""Tests for shared email HTML templates."""

from app.constants.response_pages import OFFICIAL_SITE_URL
from app.services.notifications.email_templates import (
    PRODUCT_NAME,
    PRODUCT_TAGLINE,
    build_alert_email,
    build_email_html,
    build_plain_email,
    build_test_email,
)


def test_build_email_html_includes_branding_footer():
    html = build_email_html(title="测试标题", body_html="<p>正文</p>")
    assert "测试标题" in html
    assert PRODUCT_NAME in html
    assert PRODUCT_TAGLINE in html
    assert "Flow Shield WAF" in html
    assert "请勿直接回复" in html
    assert OFFICIAL_SITE_URL in html
    assert f'href="{OFFICIAL_SITE_URL}"' in html


def test_build_plain_email_includes_header_and_footer():
    plain = build_plain_email(title="标题", subtitle="副标题", body="内容")
    assert plain.startswith("标题")
    assert "副标题" in plain
    assert "内容" in plain
    assert PRODUCT_NAME in plain
    assert PRODUCT_TAGLINE in plain
    assert OFFICIAL_SITE_URL in plain


def test_build_alert_email_has_html_and_plain():
    plain, html = build_alert_email(
        policy_name="流量突增",
        message="【预警】全站 300s 窗口内 5000 次请求，高于阈值 1000",
    )
    assert "流量突增" in plain
    assert "5000 次请求" in plain
    assert "建议操作" in plain
    assert "安全预警" in html
    assert "<ol" in html
    assert PRODUCT_NAME in html


def test_build_alert_email_includes_traffic_overview():
    overview = {
        "burst_active": False,
        "global": {
            "windows": [
                {"window_sec": 60, "requests": 120, "qps": 2.0},
                {"window_sec": 300, "requests": 900, "qps": 3.0},
                {"window_sec": 1800, "requests": 4000, "qps": 2.2},
                {"window_sec": 3600, "requests": 8000, "qps": 2.2},
            ]
        },
        "sites": [
            {
                "site_id": 1,
                "name": "官网",
                "domains": ["www.example.com"],
                "windows": [
                    {"window_sec": 60, "requests": 80, "qps": 1.3},
                    {"window_sec": 300, "requests": 500, "qps": 1.7},
                    {"window_sec": 1800, "requests": 2000, "qps": 1.1},
                    {"window_sec": 3600, "requests": 4000, "qps": 1.1},
                ],
            }
        ],
        "recent_log_stats": {
            "window_min": 30,
            "global": {"total": 1000, "blocked": 50, "passed": 950, "block_rate_pct": 5.0},
            "by_site": [
                {"site_id": 1, "total": 800, "blocked": 40, "passed": 760, "block_rate_pct": 5.0},
            ],
        },
    }
    plain, html = build_alert_email(
        policy_name="流量突增",
        message="命中阈值",
        traffic_overview=overview,
    )
    assert "站点流量与拦截汇总" in plain
    assert "官网（www.example.com）" in plain
    assert "1分钟" in plain
    assert "5分钟" in plain
    assert "30分钟" in plain
    assert "1小时" in plain
    assert "拦截率" in plain
    assert "站点流量与拦截汇总" in html
    assert "www.example.com" in html
    assert "<table" in html


def test_build_alert_email_includes_system_metrics():
    snapshot = {
        "instant": {"cpu_cores": 8, "source": "cgroup_v2"},
        "windows": {
            "60": {
                "container_cpu_pct_avg": 12.5,
                "host_cpu_pct_avg": 30.1,
                "loadavg_1_avg": 2.4,
                "load_per_core_1_avg": 0.3,
            },
            "300": {
                "container_cpu_pct_avg": 18.0,
                "host_cpu_pct_avg": 40.0,
                "loadavg_1_avg": 3.1,
                "load_per_core_1_avg": 0.39,
            },
            "1800": {
                "container_cpu_pct_avg": 22.0,
                "host_cpu_pct_avg": 45.0,
                "loadavg_1_avg": 3.5,
                "load_per_core_1_avg": 0.44,
            },
        },
    }
    plain, html = build_alert_email(
        policy_name="CPU过高",
        message="命中阈值",
        system_metrics=snapshot,
    )
    assert "系统 CPU" in plain
    assert "容器 12.5%" in plain
    assert "每核Load" not in plain
    assert "系统 CPU" in html
    assert "容器 CPU" in html
    assert "12.5%" in html
    assert "Load(1)" not in html
    assert "cgroup_v2" in html


def test_build_test_email_has_html_and_plain():
    plain, html = build_test_email()
    assert "通知通道测试" in plain
    assert "SMTP 配置验证成功" in plain
    assert "预警策略触发" in plain
    assert "<ul" in html
    assert PRODUCT_NAME in html
