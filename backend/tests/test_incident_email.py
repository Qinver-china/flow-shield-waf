"""Tests for AI incident email links and tokens."""

from app.services.ai_guard.incident_action_tokens import (
    create_incident_action_token,
    decode_incident_action_token,
)
from app.services.ai_guard.incident_email import build_analysis_result_email


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
