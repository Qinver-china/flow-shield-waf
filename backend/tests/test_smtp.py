"""Tests for SMTP multipart HTML delivery."""

from email import message_from_bytes

from app.schemas.notification import EmailChannelConfig
from app.services.notifications import smtp


def test_send_sync_builds_multipart_alternative_with_html(monkeypatch):
    captured: dict = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout=30):
            captured["host"] = host

        def starttls(self):
            captured["starttls"] = True

        def login(self, user, password):
            captured["login"] = (user, password)

        def send_message(self, msg, *, from_addr, to_addrs):
            captured["msg"] = msg
            captured["from_addr"] = from_addr
            captured["to_addrs"] = to_addrs

        def quit(self):
            pass

    monkeypatch.setattr(smtp.smtplib, "SMTP", FakeSMTP)

    cfg = EmailChannelConfig.model_validate(
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_security": "starttls",
            "smtp_user": "user",
            "smtp_password": "pass",
            "from_name": "流盾 WAF",
            "from_address": "waf@example.com",
            "to_addresses": ["admin@example.com"],
        }
    )
    smtp._send_sync(
        cfg,
        "测试主题",
        "纯文本正文",
        html_body="<html><body><p>HTML 正文</p></body></html>",
    )

    msg = captured["msg"]
    assert msg.is_multipart()
    payload = msg.as_bytes()
    parsed = message_from_bytes(payload)
    parts = list(parsed.walk())
    subtypes = [part.get_content_subtype() for part in parts if part.get_content_maintype() == "text"]
    assert subtypes == ["plain", "html"]
    html_part = parts[-1]
    assert "HTML 正文" in html_part.get_content()
