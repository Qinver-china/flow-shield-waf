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
  <div style="max-width:640px;margin:0 auto;background:{_COLOR_BG_SURFACE};
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


def build_alert_email(*, policy_name: str, message: str) -> tuple[str, str]:
    """Return (plain_text, html_body) for alert policy notifications."""
    title = f"安全预警 · {policy_name}"
    subtitle = "系统检测到异常指标，请及时登录管理面板查看详情。"
    plain = build_plain_email(
        title=title,
        subtitle=subtitle,
        body=(
            f"{message}\n\n"
            "建议操作：\n"
            "1. 登录流盾 WAF 管理面板，查看访问日志与拦截记录；\n"
            "2. 确认是否为正常业务波动或真实攻击；\n"
            "3. 必要时调整防护策略或启用更严格的拦截模式。"
        ),
    )
    body_html = (
        html_paragraph(message)
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
            "· AI 防护完成攻击分析与规则建议\n\n"
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
