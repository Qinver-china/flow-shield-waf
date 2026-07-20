"""Simple HTML pages for email link actions."""
from __future__ import annotations

import html


def render_action_page(*, title: str, message: str, success: bool) -> str:
    color = "#389e0d" if success else "#cf1322"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
</head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
margin:0;padding:40px 16px;background:#f5f5f5;color:#1f2937;">
  <div style="max-width:480px;margin:0 auto;background:#fff;border-radius:10px;
  padding:32px 24px;box-shadow:0 2px 8px rgba(0,0,0,.06);text-align:center;">
    <h1 style="margin:0 0 12px;font-size:22px;color:{color};">{html.escape(title)}</h1>
    <p style="margin:0 0 24px;line-height:1.7;">{html.escape(message)}</p>
    <a href="/ai-guard" style="color:#1677ff;text-decoration:none;">返回 AI 防护面板</a>
  </div>
</body>
</html>"""
