"""Tests for AI incident email links and tokens."""

from app.services.ai_guard.incident_action_tokens import (
    create_incident_action_token,
    decode_incident_action_token,
)
from app.services.ai_guard.incident_email import (
    build_analysis_result_email,
    build_trigger_email,
)
from app.services.notifications.email_templates import PRODUCT_NAME, PRODUCT_TAGLINE


def test_incident_action_token_roundtrip():
    token = create_incident_action_token(42, "apply")
    payload = decode_incident_action_token(token)
    assert payload["incident_id"] == 42
    assert payload["action"] == "apply"


def test_build_analysis_result_email_includes_rule_json_and_links():
    plain, html = build_analysis_result_email(
        incident_id=7,
        policy_name="测试策略",
        panel_public_url="https://waf.example.com:9000",
        analysis_report={"summary": "疑似扫描", "confidence": 0.82},
        suggested_rule={"name": "封禁 IP", "mode": "block", "conditions": {"logic": "and", "conditions": []}},
        status="suggested",
    )
    assert "封禁 IP" in plain
    assert '"name": "封禁 IP"' in plain or '"name": "封禁 IP"' in html
    assert "/api/v1/ai-guard/incidents/actions/apply?token=" in plain
    assert "/api/v1/ai-guard/incidents/actions/dismiss?token=" in plain
    assert "应用规则" in html
    assert "忽略" in html
    assert "<pre" in html
    assert PRODUCT_NAME in html
    assert PRODUCT_TAGLINE in html


def test_build_trigger_email_has_html_layout():
    plain, html = build_trigger_email(
        policy_name="高频拦截",
        window_min=5,
        trigger_snapshot={"blocked_count": 120, "threshold": 50},
        traffic_overview={
            "global": {
                "windows": [
                    {"window_sec": 60, "requests": 10, "qps": 0.17},
                    {"window_sec": 300, "requests": 50, "qps": 0.17},
                    {"window_sec": 1800, "requests": 200, "qps": 0.11},
                    {"window_sec": 3600, "requests": 400, "qps": 0.11},
                ]
            },
            "sites": [
                {
                    "site_id": 2,
                    "name": "商城",
                    "domains": ["shop.test"],
                    "windows": [
                        {"window_sec": 60, "requests": 8, "qps": 0.13},
                        {"window_sec": 300, "requests": 40, "qps": 0.13},
                        {"window_sec": 1800, "requests": 160, "qps": 0.09},
                        {"window_sec": 3600, "requests": 320, "qps": 0.09},
                    ],
                }
            ],
            "recent_log_stats": {
                "window_min": 30,
                "global": {"total": 100, "blocked": 20, "passed": 80, "block_rate_pct": 20.0},
                "by_site": [
                    {"site_id": 2, "total": 90, "blocked": 18, "passed": 72, "block_rate_pct": 20.0},
                ],
            },
        },
        system_metrics={
            "instant": {"cpu_cores": 4, "source": "cgroup_v2"},
            "windows": {
                "60": {
                    "container_cpu_pct_avg": 55.0,
                    "host_cpu_pct_avg": 70.0,
                    "loadavg_1_avg": 3.2,
                    "load_per_core_1_avg": 0.8,
                },
                "300": {
                    "container_cpu_pct_avg": 40.0,
                    "host_cpu_pct_avg": 50.0,
                    "loadavg_1_avg": 2.1,
                    "load_per_core_1_avg": 0.53,
                },
                "1800": {
                    "container_cpu_pct_avg": 30.0,
                    "host_cpu_pct_avg": 40.0,
                    "loadavg_1_avg": 1.5,
                    "load_per_core_1_avg": 0.38,
                },
            },
        },
    )
    assert "高频拦截" in plain
    assert "触发快照" in plain
    assert "站点流量与拦截汇总" in plain
    assert "系统 CPU" in plain
    assert "容器 55%" in plain
    assert "商城（shop.test）" in plain
    assert "AI 防护已触发" in html
    assert "站点流量与拦截汇总" in html
    assert "系统 CPU" in html
    assert "55%" in html
    assert "Load(1)" not in html
    assert "<table" in html
    assert "<pre" in html
    assert PRODUCT_NAME in html


def test_build_analyzing_email_has_html_layout():
    from app.services.ai_guard.incident_email import build_analyzing_email

    plain, html = build_analyzing_email(
        policy_name="高频拦截",
        sampled=200,
        blocked_count=45,
    )
    assert "200" in plain
    assert "45" in plain
    assert "AI 防护分析中" in html
    assert PRODUCT_NAME in html
