"""HTML email templates for AI guard incident notifications."""
from __future__ import annotations

import html
import json
from typing import Any

from app.services.ai_guard.incident_action_tokens import (
    INCIDENT_ACTION_TTL_MIN,
    create_incident_action_token,
)


def build_action_urls(incident_id: int, *, panel_public_url: str) -> tuple[str, str]:
    base = f"{panel_public_url.rstrip('/')}/api/v1/ai-guard/incidents/actions"
    apply_token = create_incident_action_token(incident_id, "apply")
    dismiss_token = create_incident_action_token(incident_id, "dismiss")
    return (
        f"{base}/apply?token={apply_token}",
        f"{base}/dismiss?token={dismiss_token}",
    )


def build_analysis_result_email(
    *,
    incident_id: int,
    policy_name: str,
    panel_public_url: str,
    analysis_report: dict[str, Any] | None,
    suggested_rule: dict[str, Any] | None,
    status: str,
    applied_rule_id: int | None = None,
    apply_mode: str | None = None,
    error_detail: str | None = None,
) -> tuple[str, str]:
    """Return (plain_text, html_body)."""
    report = analysis_report or {}
    summary = str(report.get("summary") or "（无摘要）")
    confidence = report.get("confidence")
    confidence_text = f"{float(confidence):.0%}" if confidence is not None else "—"

    plain_parts = [
        f"策略：{policy_name}",
        f"事件编号：#{incident_id}",
        f"状态：{status}",
        f"分析摘要：{summary}",
        f"置信度：{confidence_text}",
    ]

    apply_url = dismiss_url = None
    rule_json = ""
    if suggested_rule and status == "suggested":
        rule_json = json.dumps(suggested_rule, ensure_ascii=False, indent=2)
        apply_url, dismiss_url = build_action_urls(incident_id, panel_public_url=panel_public_url)
        plain_parts.append(f"\n建议规则 JSON：\n{rule_json}")
        plain_parts.append(f"\n应用规则（{INCIDENT_ACTION_TTL_MIN} 分钟内有效）：\n{apply_url}")
        plain_parts.append(f"\n忽略此建议（{INCIDENT_ACTION_TTL_MIN} 分钟内有效）：\n{dismiss_url}")
    elif applied_rule_id:
        plain_parts.append(f"\n已自动创建规则 #{applied_rule_id}（模式：{apply_mode or '—'}）")
    elif error_detail:
        plain_parts.append(f"\n错误详情：{error_detail}")

    indicators = report.get("attack_indicators") or []
    if indicators:
        plain_parts.append("\n攻击共性：\n" + "\n".join(f"- {item}" for item in indicators))

    plain = "\n".join(plain_parts)

    summary_html = html.escape(summary)
    policy_html = html.escape(policy_name)
    indicators_html = ""
    if indicators:
        items = "".join(f"<li>{html.escape(str(item))}</li>" for item in indicators)
        indicators_html = f"<h3 style=\"margin:20px 0 8px;font-size:15px;\">攻击共性</h3><ul>{items}</ul>"

    rule_block = ""
    action_block = ""
    if suggested_rule and status == "suggested" and rule_json and apply_url and dismiss_url:
        rule_block = (
            "<h3 style=\"margin:20px 0 8px;font-size:15px;\">建议规则 JSON</h3>"
            f"<pre style=\"background:#f6f8fa;border:1px solid #e5e7eb;"
            "border-radius:6px;padding:12px;overflow:auto;font-size:12px;"
            f"line-height:1.5;\">{html.escape(rule_json)}</pre>"
        )
        action_block = f"""
<div style="margin:28px 0 8px;">
  <a href="{html.escape(apply_url, quote=True)}"
     style="display:inline-block;margin-right:12px;padding:10px 18px;background:#1677ff;
     color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">应用规则</a>
  <a href="{html.escape(dismiss_url, quote=True)}"
     style="display:inline-block;padding:10px 18px;background:#f0f0f0;color:#333;
     text-decoration:none;border-radius:6px;font-weight:600;">忽略</a>
</div>
<p style="color:#888;font-size:12px;margin:0;">
  以上链接含鉴权令牌，{INCIDENT_ACTION_TTL_MIN} 分钟内有效。
</p>
"""
    elif applied_rule_id:
        action_block = (
            f"<p style=\"margin-top:16px;color:#389e0d;\">"
            f"已自动创建规则 #{applied_rule_id}（模式：{html.escape(str(apply_mode or '—'))}）</p>"
        )
    elif error_detail:
        action_block = (
            f"<p style=\"margin-top:16px;color:#cf1322;\">"
            f"错误：{html.escape(error_detail)}</p>"
        )

    html_body = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>流盾 AI 防护分析结果</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
color:#1f2937;line-height:1.6;margin:0;padding:24px;background:#f9fafb;">
  <div style="max-width:640px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:24px;">
    <h2 style="margin:0 0 16px;font-size:20px;">流盾 AI 防护 · 分析结果</h2>
    <p style="margin:0 0 8px;color:#6b7280;">策略：{policy_html} · 事件 #{incident_id}</p>
    <h3 style="margin:20px 0 8px;font-size:15px;">分析摘要</h3>
    <p style="margin:0;">{summary_html}</p>
    <p style="margin:12px 0 0;"><strong>置信度：</strong>{html.escape(confidence_text)}</p>
    {indicators_html}
    {rule_block}
    {action_block}
  </div>
</body>
</html>"""
    return plain, html_body
