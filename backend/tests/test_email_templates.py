"""Tests for shared email HTML templates."""

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


def test_build_plain_email_includes_header_and_footer():
    plain = build_plain_email(title="标题", subtitle="副标题", body="内容")
    assert plain.startswith("标题")
    assert "副标题" in plain
    assert "内容" in plain
    assert PRODUCT_NAME in plain
    assert PRODUCT_TAGLINE in plain


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


def test_build_test_email_has_html_and_plain():
    plain, html = build_test_email()
    assert "通知通道测试" in plain
    assert "SMTP 配置验证成功" in plain
    assert "预警策略触发" in plain
    assert "<ul" in html
    assert PRODUCT_NAME in html
