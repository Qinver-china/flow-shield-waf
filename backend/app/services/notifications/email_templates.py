"""Shared HTML email layout for Flow Shield WAF notifications."""
from __future__ import annotations

import html
from datetime import datetime, timezone

PRODUCT_NAME = "流盾 WAF"
PRODUCT_NAME_EN = "Flow Shield WAF"
PRODUCT_TAGLINE = "守住每一次真实访问"

_COLOR_PRIMARY = "#3474ff"
_COLOR_TEXT = "#0f172a"
_COLOR_TEXT_SECONDARY = "#475569"
_COLOR_TEXT_MUTED = "#94a3b8"
_COLOR_BORDER = "#e2e8f0"
_COLOR_BG_PAGE = "#f1f5f9"
_COLOR_BG_SURFACE = "#ffffff"
_COLOR_SUCCESS = "#16a34a"
_COLOR_DANGER = "#dc2626"
_FONT_FAMILY = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',"
    "'Hiragino Sans GB','Microsoft YaHei',Roboto,'Helvetica Neue',Arial,sans-serif"
)


def build_email_html(
    *,
    title: str,
    body_html: str,
    subtitle: str | None = None,
    preheader: str | None = None,
) -> str:
    """Wrap content in the standard Flow Shield WAF email layout."""
    title_html = html.escape(title)
    subtitle_html = (
        f'<p style="margin:8px 0 0;font-size:14px;color:{_COLOR_TEXT_SECONDARY};'
        f'line-height:1.6;">{html.escape(subtitle)}</p>'
        if subtitle
        else ""
    )
    preheader_html = ""
    if preheader:
        preheader_html = (
            f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;'
            f'color:transparent;mso-hide:all;">{html.escape(preheader)}</div>'
        )
    year = datetime.now(timezone.utc).year
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_html}</title>
</head>
<body style="margin:0;padding:24px 16px;background:{_COLOR_BG_PAGE};color:{_COLOR_TEXT};
font-family:{_FONT_FAMILY};line-height:1.6;-webkit-text-size-adjust:100%;">
  {preheader_html}
  <div style="max-width:720px;margin:0 auto;background:{_COLOR_BG_SURFACE};
  border:1px solid {_COLOR_BORDER};border-radius:12px;overflow:hidden;
  box-shadow:0 4px 12px rgba(15,23,42,0.06);">
    <div style="padding:18px 24px;background:{_COLOR_PRIMARY};color:#ffffff;">
      <div style="font-size:18px;font-weight:700;letter-spacing:0.02em;">{PRODUCT_NAME}</div>
      <div style="margin-top:4px;font-size:12px;opacity:0.9;">{PRODUCT_TAGLINE}</div>
    </div>
    <div style="padding:28px 24px 8px;">
      <h1 style="margin:0;font-size:22px;font-weight:700;color:{_COLOR_TEXT};">{title_html}</h1>
      {subtitle_html}
      <div style="margin-top:24px;font-size:15px;color:{_COLOR_TEXT};">
        {body_html}
      </div>
    </div>
    <div style="margin:16px 24px 0;border-top:1px solid {_COLOR_BORDER};"></div>
    <div style="padding:20px 24px 24px;text-align:center;">
      <div style="font-size:13px;font-weight:600;color:{_COLOR_TEXT_SECONDARY};">
        {PRODUCT_NAME} · {PRODUCT_NAME_EN}
      </div>
      <div style="margin-top:4px;font-size:12px;color:{_COLOR_TEXT_MUTED};">{PRODUCT_TAGLINE}</div>
      <div style="margin-top:10px;font-size:11px;color:{_COLOR_TEXT_MUTED};">
        此邮件由 {PRODUCT_NAME} 自动发送，请勿直接回复。
      </div>
      <div style="margin-top:6px;font-size:11px;color:{_COLOR_TEXT_MUTED};">
        © {year} {PRODUCT_NAME_EN}
      </div>
    </div>
  </div>
</body>
</html>"""


def build_plain_email(
    *,
    title: str,
    body: str,
    subtitle: str | None = None,
) -> str:
    """Build a plain-text email with consistent header and footer."""
    lines = [
        title,
        "",
    ]
    if subtitle:
        lines.extend([subtitle, ""])
    lines.extend(
        [
            body.strip(),
            "",
            "—" * 32,
            f"{PRODUCT_NAME} · {PRODUCT_NAME_EN}",
            PRODUCT_TAGLINE,
            f"此邮件由 {PRODUCT_NAME} 自动发送，请勿直接回复。",
        ]
    )
    return "\n".join(lines)


def html_section(title: str, content_html: str) -> str:
    return (
        f'<h3 style="margin:24px 0 8px;font-size:15px;font-weight:600;color:{_COLOR_TEXT};">'
        f"{html.escape(title)}</h3>"
        f'<div style="margin:0;color:{_COLOR_TEXT};">{content_html}</div>'
    )


def html_paragraph(text: str, *, muted: bool = False) -> str:
    color = _COLOR_TEXT_MUTED if muted else _COLOR_TEXT
    return (
        f'<p style="margin:0 0 12px;font-size:15px;line-height:1.7;color:{color};">'
        f"{html.escape(text)}</p>"
    )


def html_info_row(label: str, value: str) -> str:
    return (
        f'<p style="margin:0 0 8px;font-size:14px;line-height:1.6;">'
        f'<span style="color:{_COLOR_TEXT_SECONDARY};">{html.escape(label)}：</span>'
        f"<strong>{html.escape(value)}</strong></p>"
    )


def html_pre_block(text: str) -> str:
    return (
        f'<pre style="margin:0;background:#f8fafc;border:1px solid {_COLOR_BORDER};'
        "border-radius:8px;padding:14px;overflow:auto;font-size:12px;"
        f'line-height:1.55;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;">'
        f"{html.escape(text)}</pre>"
    )


def html_button(text: str, url: str, *, primary: bool = True) -> str:
    if primary:
        style = (
            f"display:inline-block;margin-right:12px;padding:10px 20px;background:{_COLOR_PRIMARY};"
            "color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;"
        )
    else:
        style = (
            "display:inline-block;padding:10px 20px;background:#f1f5f9;color:#334155;"
            "text-decoration:none;border-radius:8px;font-weight:600;font-size:14px;"
            "border:1px solid #e2e8f0;"
        )
    return (
        f'<a href="{html.escape(url, quote=True)}" style="{style}">'
        f"{html.escape(text)}</a>"
    )


def html_status_message(text: str, *, success: bool = False, danger: bool = False) -> str:
    if danger:
        color = _COLOR_DANGER
    elif success:
        color = _COLOR_SUCCESS
    else:
        color = _COLOR_TEXT
    return (
        f'<p style="margin:16px 0 0;font-size:14px;line-height:1.7;color:{color};">'
        f"{html.escape(text)}</p>"
    )


# Windows highlighted in alert / AI-trigger emails (1m / 5m / 30m / 1h).
_EMAIL_TRAFFIC_WINDOWS: tuple[tuple[int, str], ...] = (
    (60, "1分钟"),
    (300, "5分钟"),
    (1800, "30分钟"),
    (3600, "1小时"),
)


def _window_lookup(windows: list[dict] | None) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for row in windows or []:
        try:
            out[int(row["window_sec"])] = row
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _fmt_int(value: object) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def _fmt_qps(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _site_display_name(site: dict) -> str:
    name = str(site.get("name") or "").strip() or f"站点 #{site.get('site_id', '?')}"
    domains = site.get("domains") or []
    domain = site.get("domain") or (domains[0] if domains else None)
    if domain:
        return f"{name}（{domain}）"
    return name


def format_traffic_overview_plain(overview: dict | None) -> str:
    """Render a plain-text multi-site traffic / block summary for emails."""
    if not overview or overview.get("error"):
        return "（暂无实时流量汇总）"

    lines: list[str] = []
    global_windows = _window_lookup((overview.get("global") or {}).get("windows"))
    lines.append("【全站窗口请求量】")
    for sec, label in _EMAIL_TRAFFIC_WINDOWS:
        row = global_windows.get(sec)
        if not row:
            lines.append(f"  {label}: —")
            continue
        lines.append(
            f"  {label}: {_fmt_int(row.get('requests'))} 请求 / QPS {_fmt_qps(row.get('qps'))}"
        )

    recent = overview.get("recent_log_stats") or {}
    g_logs = recent.get("global") or {}
    if g_logs:
        lines.append(
            f"【全站近期日志】近 {recent.get('window_min', '—')} 分钟："
            f"总量 {_fmt_int(g_logs.get('total'))} / "
            f"拦截 {_fmt_int(g_logs.get('blocked'))} / "
            f"放行 {_fmt_int(g_logs.get('passed'))} / "
            f"拦截率 {_fmt_qps(g_logs.get('block_rate_pct'))}%"
        )

    if overview.get("burst_active"):
        lines.append("【状态】流量自动取证模式已激活")

    sites = overview.get("sites") or []
    log_by_site = {
        int(row["site_id"]): row
        for row in (recent.get("by_site") or [])
        if row.get("site_id") is not None
    }
    if sites:
        lines.append("")
        lines.append("【分站点汇总】")
        for site in sites:
            sid = int(site.get("site_id") or 0)
            lines.append(_site_display_name(site))
            win = _window_lookup(site.get("windows"))
            for sec, label in _EMAIL_TRAFFIC_WINDOWS:
                row = win.get(sec)
                if not row:
                    lines.append(f"  {label}: —")
                else:
                    lines.append(
                        f"  {label}: {_fmt_int(row.get('requests'))} 请求 / "
                        f"QPS {_fmt_qps(row.get('qps'))}"
                    )
            log_row = log_by_site.get(sid)
            if log_row:
                lines.append(
                    f"  近期日志: 总量 {_fmt_int(log_row.get('total'))} / "
                    f"拦截 {_fmt_int(log_row.get('blocked'))} / "
                    f"放行 {_fmt_int(log_row.get('passed'))} / "
                    f"拦截率 {_fmt_qps(log_row.get('block_rate_pct'))}%"
                )
            lines.append("")

    return "\n".join(lines).rstrip()


def format_traffic_overview_html(overview: dict | None) -> str:
    """Render an HTML multi-site traffic / block summary table for emails."""
    if not overview or overview.get("error"):
        return html_paragraph("暂无实时流量汇总。", muted=True)

    th = (
        f"padding:8px 10px;border-bottom:1px solid {_COLOR_BORDER};"
        f"background:#f8fafc;color:{_COLOR_TEXT_SECONDARY};font-size:12px;"
        "font-weight:600;text-align:left;white-space:nowrap;"
    )
    td = (
        f"padding:8px 10px;border-bottom:1px solid {_COLOR_BORDER};"
        f"color:{_COLOR_TEXT};font-size:12px;white-space:nowrap;"
    )
    td_muted = (
        f"padding:8px 10px;border-bottom:1px solid {_COLOR_BORDER};"
        f"color:{_COLOR_TEXT_MUTED};font-size:12px;white-space:nowrap;"
    )

    def _cells_for_windows(windows: list[dict] | None) -> str:
        win = _window_lookup(windows)
        parts: list[str] = []
        for sec, _label in _EMAIL_TRAFFIC_WINDOWS:
            row = win.get(sec)
            if not row:
                parts.append(f'<td style="{td_muted}">—</td><td style="{td_muted}">—</td>')
            else:
                parts.append(
                    f'<td style="{td}">{html.escape(_fmt_int(row.get("requests")))}</td>'
                    f'<td style="{td}">{html.escape(_fmt_qps(row.get("qps")))}</td>'
                )
        return "".join(parts)

    header_cols = "".join(
        f'<th style="{th}">{html.escape(label)}请求</th>'
        f'<th style="{th}">{html.escape(label)}QPS</th>'
        for _sec, label in _EMAIL_TRAFFIC_WINDOWS
    )
    header = (
        f'<tr>'
        f'<th style="{th}">范围</th>'
        f"{header_cols}"
        f'<th style="{th}">近期总量</th>'
        f'<th style="{th}">拦截</th>'
        f'<th style="{th}">放行</th>'
        f'<th style="{th}">拦截率</th>'
        f"</tr>"
    )

    recent = overview.get("recent_log_stats") or {}
    g_logs = recent.get("global") or {}
    log_by_site = {
        int(row["site_id"]): row
        for row in (recent.get("by_site") or [])
        if row.get("site_id") is not None
    }

    def _log_cells(log_row: dict | None) -> str:
        if not log_row:
            return (
                f'<td style="{td_muted}">—</td>'
                f'<td style="{td_muted}">—</td>'
                f'<td style="{td_muted}">—</td>'
                f'<td style="{td_muted}">—</td>'
            )
        return (
            f'<td style="{td}">{html.escape(_fmt_int(log_row.get("total")))}</td>'
            f'<td style="{td}">{html.escape(_fmt_int(log_row.get("blocked")))}</td>'
            f'<td style="{td}">{html.escape(_fmt_int(log_row.get("passed")))}</td>'
            f'<td style="{td}">{html.escape(_fmt_qps(log_row.get("block_rate_pct")))}%</td>'
        )

    rows_html = [
        "<tr>"
        f'<td style="{td}"><strong>全站</strong></td>'
        + _cells_for_windows((overview.get("global") or {}).get("windows"))
        + _log_cells(g_logs if "total" in g_logs else None)
        + "</tr>"
    ]
    for site in overview.get("sites") or []:
        sid = int(site.get("site_id") or 0)
        rows_html.append(
            "<tr>"
            f'<td style="{td}">{html.escape(_site_display_name(site))}</td>'
            + _cells_for_windows(site.get("windows"))
            + _log_cells(log_by_site.get(sid))
            + "</tr>"
        )

    note = ""
    if overview.get("burst_active"):
        note = html_paragraph("当前已进入流量自动取证模式。", muted=False)
    window_note = html_paragraph(
        f"近期日志统计窗口：近 {recent.get('window_min', '—')} 分钟；"
        "窗口请求量来自引擎实时计数（1分钟 / 5分钟 / 30分钟 / 1小时）。",
        muted=True,
    )

    table = (
        f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">'
        f'<table style="width:100%;border-collapse:collapse;min-width:720px;">'
        f"<thead>{header}</thead>"
        f'<tbody>{"".join(rows_html)}</tbody>'
        f"</table></div>"
    )
    return note + table + window_note


_EMAIL_SYSTEM_WINDOWS = (
    (60, "1分钟"),
    (300, "5分钟"),
    (1800, "30分钟"),
)


def _fmt_metric(value: object, *, digits: int = 2, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    text = f"{num:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}" if text else "—"


def format_system_metrics_plain(snapshot: dict | None) -> str:
    """Render plain-text CPU / load window averages for emails."""
    if not snapshot:
        return "（暂无系统 CPU 数据）"

    windows = snapshot.get("windows") or {}
    instant = snapshot.get("instant") or {}
    lines = ["【窗口平均 CPU】"]
    for sec, label in _EMAIL_SYSTEM_WINDOWS:
        row = windows.get(str(sec)) or {}
        lines.append(
            f"  {label}: 容器 {_fmt_metric(row.get('container_cpu_pct_avg'), digits=1, suffix='%')} · "
            f"宿主机 {_fmt_metric(row.get('host_cpu_pct_avg'), digits=1, suffix='%')}"
        )

    cores = instant.get("cpu_cores")
    source = instant.get("source")
    meta_parts: list[str] = []
    if cores is not None:
        meta_parts.append(f"CPU 核数 {cores}")
    if source:
        meta_parts.append(f"来源 {source}")
    if meta_parts:
        lines.append("【环境】" + " · ".join(meta_parts))
    return "\n".join(lines)


def format_system_metrics_html(snapshot: dict | None) -> str:
    """Render an HTML table of CPU window averages for emails."""
    if not snapshot:
        return html_paragraph("暂无系统 CPU 数据。", muted=True)

    windows = snapshot.get("windows") or {}
    instant = snapshot.get("instant") or {}
    th = (
        f"padding:8px 10px;border-bottom:1px solid {_COLOR_BORDER};"
        f"background:#f8fafc;color:{_COLOR_TEXT_SECONDARY};font-size:12px;"
        "font-weight:600;text-align:left;white-space:nowrap;"
    )
    td = (
        f"padding:8px 10px;border-bottom:1px solid {_COLOR_BORDER};"
        f"color:{_COLOR_TEXT};font-size:12px;white-space:nowrap;"
    )
    header = (
        f"<tr>"
        f'<th style="{th}">窗口</th>'
        f'<th style="{th}">容器 CPU</th>'
        f'<th style="{th}">宿主机 CPU</th>'
        f"</tr>"
    )
    rows: list[str] = []
    for sec, label in _EMAIL_SYSTEM_WINDOWS:
        row = windows.get(str(sec)) or {}
        rows.append(
            "<tr>"
            f'<td style="{td}">{html.escape(label)}</td>'
            f'<td style="{td}">{html.escape(_fmt_metric(row.get("container_cpu_pct_avg"), digits=1, suffix="%"))}</td>'
            f'<td style="{td}">{html.escape(_fmt_metric(row.get("host_cpu_pct_avg"), digits=1, suffix="%"))}</td>'
            "</tr>"
        )

    meta_bits: list[str] = []
    if instant.get("cpu_cores") is not None:
        meta_bits.append(f"CPU 核数 {instant.get('cpu_cores')}")
    if instant.get("source"):
        meta_bits.append(f"采样来源 {instant.get('source')}")
    meta_bits.append("数值为对应窗口的滚动平均 CPU%（1 / 5 / 30 分钟）。")
    note = html_paragraph(" · ".join(str(x) for x in meta_bits), muted=True)

    table = (
        f'<div style="overflow-x:auto;-webkit-overflow-scrolling:touch;">'
        f'<table style="width:100%;border-collapse:collapse;min-width:480px;">'
        f"<thead>{header}</thead>"
        f'<tbody>{"".join(rows)}</tbody>'
        f"</table></div>"
    )
    return table + note


def build_alert_email(
    *,
    policy_name: str,
    message: str,
    traffic_overview: dict | None = None,
    system_metrics: dict | None = None,
) -> tuple[str, str]:
    """Return (plain_text, html_body) for alert policy notifications."""
    title = f"安全预警 · {policy_name}"
    subtitle = "系统检测到异常指标，请及时登录管理面板查看详情。"
    traffic_plain = format_traffic_overview_plain(traffic_overview)
    system_plain = format_system_metrics_plain(system_metrics)
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            f"{message}\n\n"
            "站点流量与拦截汇总：\n"
            f"{traffic_plain}\n\n"
            "系统 CPU：\n"
            f"{system_plain}\n\n"
            "建议操作：\n"
            "1. 登录流盾 WAF 管理面板，查看访问日志与拦截记录；\n"
            "2. 确认是否为正常业务波动或真实攻击；\n"
            "3. 必要时调整防护策略或启用更严格的拦截模式。"
        ),
    )
    body_html = (
        html_paragraph(message)
        + html_section("站点流量与拦截汇总", format_traffic_overview_html(traffic_overview))
        + html_section("系统 CPU", format_system_metrics_html(system_metrics))
        + html_section(
            "建议操作",
            "<ol style=\"margin:0;padding-left:20px;color:#475569;font-size:14px;line-height:1.8;\">"
            "<li>登录流盾 WAF 管理面板，查看访问日志与拦截记录；</li>"
            "<li>确认是否为正常业务波动或真实攻击；</li>"
            "<li>必要时调整防护策略或启用更严格的拦截模式。</li>"
            "</ol>",
        )
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader=message,
    )
    return plain, html_body


def build_test_email() -> tuple[str, str]:
    """Return (plain_text, html_body) for notification channel test."""
    title = "通知通道测试"
    subtitle = "SMTP 配置验证成功"
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            "恭喜！若您正在阅读此邮件，说明邮件通知通道已正确配置。\n\n"
            "流盾 WAF 将在以下场景通过此通道向您发送通知：\n"
            "· 预警策略触发（流量异常、拦截率过高等）\n"
            "· AI 防护完成攻击分析与规则建议\n"
            "· SSL 证书即将到期提醒\n\n"
            "您无需回复此邮件。"
        ),
    )
    body_html = (
        html_paragraph("恭喜！若您正在阅读此邮件，说明邮件通知通道已正确配置。")
        + html_section(
            "后续通知场景",
            "<ul style=\"margin:0;padding-left:20px;color:#475569;font-size:14px;line-height:1.8;\">"
            "<li>预警策略触发（流量异常、拦截率过高等）</li>"
            "<li>AI 防护完成攻击分析与规则建议</li>"
            "<li>SSL 证书即将到期提醒</li>"
            "</ul>",
        )
        + html_paragraph("您无需回复此邮件。", muted=True)
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader="流盾 WAF 通知通道测试邮件",
    )
    return plain, html_body


def build_cert_expiry_email(
    *,
    cert_name: str,
    domains: str,
    not_after_local: str,
    days_left: int,
    timezone_name: str,
) -> tuple[str, str]:
    """Return (plain_text, html_body) for SSL certificate expiry reminder."""
    if days_left == 0:
        urgency = "将于今天到期"
    else:
        urgency = f"将于 {days_left} 天后到期"
    title = f"证书即将到期 · {cert_name}"
    subtitle = f"{urgency}，请及时更新以免影响 HTTPS 访问。"
    message = (
        f"证书「{cert_name}」{urgency}。\n"
        f"覆盖域名：{domains}\n"
        f"到期时间（{timezone_name}）：{not_after_local}"
    )
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            f"{message}\n\n"
            "建议操作：\n"
            "1. 登录流盾 WAF 管理面板，打开「证书管理」；\n"
            "2. 更新或重新导入有效证书；\n"
            "3. 确认相关站点已绑定新证书并完成生效。"
        ),
    )
    body_html = (
        "".join(html_paragraph(line) for line in message.split("\n") if line)
        + html_section(
            "建议操作",
            "<ol style=\"margin:0;padding-left:20px;color:#475569;font-size:14px;line-height:1.8;\">"
            "<li>登录流盾 WAF 管理面板，打开「证书管理」；</li>"
            "<li>更新或重新导入有效证书；</li>"
            "<li>确认相关站点已绑定新证书并完成生效。</li>"
            "</ol>",
        )
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader=f"证书「{cert_name}」{urgency}",
    )
    return plain, html_body


def build_acme_result_email(
    *,
    success: bool,
    kind: str,
    cert_name: str,
    domains: str,
    ca_name: str,
    error: str | None = None,
) -> tuple[str, str]:
    """Return (plain_text, html_body) for ACME issue or renew notifications."""
    action = "续期" if kind == "renew" else "申请"
    domain_text = domains.strip() or "（无域名）"
    if success:
        title = f"证书{action}成功 · {cert_name}"
        subtitle = f"已通过 {ca_name} 完成{action}，站点 HTTPS 将使用新证书。"
        message = (
            f"证书「{cert_name}」{action}成功。\n"
            f"证书机构：{ca_name}\n"
            f"覆盖域名：{domain_text}"
        )
        hint = (
            "证书已写入并绑定站点。若站点已开启 HTTPS，引擎会自动重载；"
            "请抽空确认站点访问正常。"
        )
    else:
        title = f"证书{action}失败 · {cert_name}"
        subtitle = f"通过 {ca_name} {action}未成功，请检查域名解析与 80 端口。"
        err_text = (error or "未知错误").strip()
        message = (
            f"证书「{cert_name}」{action}失败。\n"
            f"证书机构：{ca_name}\n"
            f"覆盖域名：{domain_text}\n"
            f"失败原因：{err_text}"
        )
        hint = "请确认域名 A/AAAA 已指向本机、公网可访问 80 端口后重试。"
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=f"{message}\n\n{hint}",
    )
    body_html = (
        "".join(html_paragraph(line) for line in message.split("\n") if line)
        + html_status_message(hint, success=success, danger=not success)
    )
    html_body = build_email_html(
        title=title,
        subtitle=subtitle,
        body_html=body_html,
        preheader=title,
    )
    return plain, html_body
