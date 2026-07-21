"""HTML email templates for AI guard incident notifications."""
from __future__ import annotations

import html
import json
from typing import Any

from app.services.ai_guard.incident_action_tokens import (
    INCIDENT_ACTION_TTL_MIN,
    create_incident_action_token,
)
from app.services.notifications.email_templates import (
    build_email_html,
    build_plain_email,
    format_system_metrics_html,
    format_system_metrics_plain,
    format_traffic_overview_html,
    format_traffic_overview_plain,
    html_button,
    html_info_row,
    html_paragraph,
    html_pre_block,
    html_section,
    html_status_message,
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
        "",
        f"分析摘要：{summary}",
        f"置信度：{confidence_text}",
    ]

    apply_url = dismiss_url = None
    rule_json = ""
    if suggested_rule and status == "suggested":
        rule_json = json.dumps(suggested_rule, ensure_ascii=False, indent=2)
        apply_url, dismiss_url = build_action_urls(incident_id, panel_public_url=panel_public_url)
        plain_parts.extend(
            [
                "",
                "建议规则 JSON：",
                rule_json,
                "",
                f"应用规则（{INCIDENT_ACTION_TTL_MIN} 分钟内有效）：",
                apply_url,
                "",
                f"忽略此建议（{INCIDENT_ACTION_TTL_MIN} 分钟内有效）：",
                dismiss_url,
            ]
        )
    elif applied_rule_id:
        plain_parts.append(
            f"\n已自动创建规则 #{applied_rule_id}（模式：{apply_mode or '—'}）"
        )
    elif status == "analyzed":
        plain_parts.append("\n本次分析未建议新建防护规则。")
    elif error_detail:
        plain_parts.append(f"\n错误详情：{error_detail}")

    indicators = report.get("attack_indicators") or []
    if indicators:
        plain_parts.append("\n攻击共性：")
        plain_parts.extend(f"- {item}" for item in indicators)

    plain = build_plain_email(
        title="AI 防护分析结果",
        subtitle=f"策略「{policy_name}」· 事件 #{incident_id}",
        body="\n".join(plain_parts),
    )

    summary_html = html.escape(summary)
    indicators_html = ""
    if indicators:
        items = "".join(f"<li>{html.escape(str(item))}</li>" for item in indicators)
        indicators_html = html_section(
            "攻击共性",
            f'<ul style="margin:0;padding-left:20px;line-height:1.8;">{items}</ul>',
        )

    rule_block = ""
    action_block = ""
    if suggested_rule and status == "suggested" and rule_json and apply_url and dismiss_url:
        rule_block = html_section("建议规则 JSON", html_pre_block(rule_json))
        action_block = (
            '<div style="margin:28px 0 8px;">'
            f"{html_button('应用规则', apply_url)}"
            f"{html_button('忽略', dismiss_url, primary=False)}"
            "</div>"
            f'<p style="color:#94a3b8;font-size:12px;margin:0;">'
            f"以上链接含鉴权令牌，{INCIDENT_ACTION_TTL_MIN} 分钟内有效。</p>"
        )
    elif applied_rule_id:
        action_block = html_status_message(
            f"已自动创建规则 #{applied_rule_id}（模式：{apply_mode or '—'}）",
            success=True,
        )
    elif status == "analyzed":
        action_block = html_status_message("本次分析未建议新建防护规则。", success=True)
    elif error_detail:
        action_block = html_status_message(f"错误：{error_detail}", danger=True)

    body_html = (
        html_info_row("策略", policy_name)
        + html_info_row("事件编号", f"#{incident_id}")
        + html_info_row("状态", status)
        + html_section("分析摘要", f'<p style="margin:0;line-height:1.7;">{summary_html}</p>')
        + html_info_row("置信度", confidence_text)
        + indicators_html
        + rule_block
        + action_block
    )

    html_body = build_email_html(
        title="AI 防护分析结果",
        subtitle=f"策略「{policy_name}」· 事件 #{incident_id}",
        body_html=body_html,
        preheader=summary,
    )
    return plain, html_body


def build_trigger_email(
    *,
    policy_name: str,
    window_min: int,
    trigger_snapshot: dict[str, Any],
    traffic_overview: dict[str, Any] | None = None,
    system_metrics: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (plain_text, html_body) when an AI guard policy triggers."""
    snapshot_json = json.dumps(trigger_snapshot, ensure_ascii=False, indent=2)
    title = "AI 防护已触发"
    subtitle = f"策略「{policy_name}」· 开始分析近 {window_min} 分钟日志"
    traffic_plain = format_traffic_overview_plain(traffic_overview)
    system_plain = format_system_metrics_plain(system_metrics)
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            f"触发条件已命中，系统正在自动取样并分析近 {window_min} 分钟的防护日志。\n\n"
            "站点流量与拦截汇总：\n"
            f"{traffic_plain}\n\n"
            "系统 CPU：\n"
            f"{system_plain}\n\n"
            "触发快照：\n"
            f"{snapshot_json}\n\n"
            "分析完成后将另行发送「AI 防护分析结果」邮件。"
        ),
    )
    body_html = (
        html_paragraph(f"触发条件已命中，系统正在自动取样并分析近 {window_min} 分钟的防护日志。")
        + html_section("站点流量与拦截汇总", format_traffic_overview_html(traffic_overview))
        + html_section("系统 CPU", format_system_metrics_html(system_metrics))
        + html_section("触发快照", html_pre_block(snapshot_json))
        + html_paragraph("分析完成后将另行发送「AI 防护分析结果」邮件。", muted=True)
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader=f"策略「{policy_name}」已触发，正在分析日志",
    )
    return plain, html_body


def build_analyzing_email(
    *,
    policy_name: str,
    sampled: int,
    blocked_count: int,
) -> tuple[str, str]:
    """Return (plain_text, html_body) while log sampling / analysis is in progress."""
    title = "AI 防护分析中"
    subtitle = f"策略「{policy_name}」"
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            f"已取样 {sampled} 条日志（拦截 {blocked_count} 条），正在调用 AI 进行分析。\n\n"
            "请稍候，分析完成后将发送结果邮件。"
        ),
    )
    body_html = (
        html_info_row("取样条数", str(sampled))
        + html_info_row("拦截条数", str(blocked_count))
        + html_paragraph("正在调用 AI 进行分析，请稍候。分析完成后将发送结果邮件。", muted=True)
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader=f"已取样 {sampled} 条日志，分析进行中",
    )
    return plain, html_body
