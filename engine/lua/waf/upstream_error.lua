-- Render gateway / origin error pages with configured captcha footer.
local sync = require "waf.sync"
local page_render = require "waf.page_render"

local _M = {}

local MESSAGES = {
    [502] = "无法连接到源站",
    [503] = "源站连接失败",
    [504] = "源站连接超时",
}

local PAGE = [[<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{max-width:520px;text-align:center;padding:40px}
h1{font-size:100px;margin:0;color:#f87171;font-weight:700;letter-spacing:.04em;line-height:1}
h2{font-size:22px;font-weight:600;margin:16px 0 0;color:#e2e8f0}
.brand{margin-top:40px;color:#64748b;font-size:13px;letter-spacing:.5px}
.brand b,.brand a{color:#38bdf8}
.brand a{text-decoration:none}
.brand a:hover{text-decoration:underline}
</style>
</head>
<body>
<div class="box">
  <h1>%s</h1>
  <h2>%s</h2>
  <div class="brand">%s</div>
</div>
</body>
</html>]]

local function html_escape(s)
    s = tostring(s or "")
    s = s:gsub("&", "&amp;")
    s = s:gsub("<", "&lt;")
    s = s:gsub(">", "&gt;")
    s = s:gsub('"', "&quot;")
    return s
end

function _M.serve(status)
    status = tonumber(status) or tonumber(ngx.status) or 502
    local message = MESSAGES[status] or MESSAGES[502]
    local code = tostring(status)

    if sync.needs_load() then
        sync.load(true)
    end
    local cfg = sync.get() or {}
    local site = sync.site_by_domain(ngx.var.host)
    local ctx = {
        request_id = ngx.var.request_id or "",
        site_id = site and site.id or tonumber(ngx.var.waf_site_id),
        domain = ngx.var.host or "",
    }
    local footer = page_render.render_captcha_footer(cfg, site, ctx, {})

    ngx.status = status
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(string.format(
        PAGE,
        html_escape(message),
        html_escape(code),
        html_escape(message),
        footer
    ))
    return ngx.exit(status)
end

return _M
