"""Defaults and template variables for custom block pages and captcha footers."""

DEFAULT_BLOCK_PAGE_STATUS = 403

DEFAULT_BLOCK_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>请求被拦截</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{max-width:520px;text-align:center;padding:40px}
h1{font-size:64px;margin:0;color:#f87171}
p{color:#94a3b8;line-height:1.7}
.rid{font-family:monospace;font-size:12px;color:#475569;margin-top:24px}
.brand{margin-top:28px;color:#64748b;font-size:13px;letter-spacing:.5px}
.brand b{color:#38bdf8}
</style></head>
<body><div class="box">
<h1>403</h1>
<h2>请求被流盾WAF 拦截</h2>
<p>您的请求命中了防护规则，已被阻止。若您认为这是误判，请联系站点管理员。</p>
<div class="rid">Request ID: {request_id}</div>
<div class="brand">由 <b>流盾WAF</b> · Flow Shield WAF 提供防护</div>
</div></body></html>"""

DEFAULT_CAPTCHA_FOOTER_HTML = (
    '由 <b>流盾WAF</b> · Flow Shield WAF 提供防护'
)

PAGE_TEMPLATE_VARIABLES = [
    {"key": "request_id", "label": "Request ID", "description": "当前请求唯一标识"},
    {"key": "client_ip", "label": "客户端 IP", "description": "访客 IP 地址"},
    {"key": "domain", "label": "域名", "description": "请求 Host"},
    {"key": "method", "label": "请求方法", "description": "HTTP 方法，如 GET / POST"},
    {"key": "request_uri", "label": "请求 URI", "description": "含查询串的请求路径（http.request_uri）"},
    {"key": "rule_id", "label": "规则 ID", "description": "命中的规则 ID"},
    {"key": "rule_name", "label": "规则名称", "description": "命中的规则名称"},
    {"key": "source", "label": "防护来源", "description": "rule / ratelimit / blacklist"},
]

ALLOWED_BLOCK_STATUS_CODES = {403, 429, 451, 503}
