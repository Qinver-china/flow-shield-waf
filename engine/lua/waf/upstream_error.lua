-- Render nginx / gateway error pages with configured captcha footer.
-- Used for engine-generated errors (413, 502, …), not WAF block pages.
local sync = require "waf.sync"
local page_render = require "waf.page_render"

local _M = {}

local DEFAULT_MESSAGE = "请求处理失败"

local MESSAGES = {
    [400] = "请求格式无效",
    [401] = "需要身份验证",
    [403] = "访问被拒绝",
    [404] = "页面不存在",
    [405] = "请求方法不允许",
    [408] = "请求超时",
    [413] = "请求体过大",
    [414] = "请求 URI 过长",
    [429] = "请求过于频繁",
    [500] = "服务器内部错误",
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
<style> body{color:#80858c;display:flex;align-items:center;justify-content:center;height:100vh;margin:0} .box{max-width:520px;text-align:center;padding:40px} h1{font-size:100px;margin:0;color:#f87171;} h2{font-size:22px;margin:16px 0 0} .brand{margin-top:40px;color:#64748b;font-size:13px;} .brand b,.brand a{color:#38bdf8} .brand a{text-decoration:none} .brand a:hover{text-decoration:underline} </style>
</head>
<body> <div class="box"> <h1>%s</h1> <h2>%s</h2> <div class="brand">%s</div> </div> </body>
</html>]]

local function html_escape(s)
    s = tostring(s or "")
    s = s:gsub("&", "&amp;")
    s = s:gsub("<", "&lt;")
    s = s:gsub(">", "&gt;")
    s = s:gsub('"', "&quot;")
    return s
end

function _M.message_for(status)
    status = tonumber(status)
    if status and MESSAGES[status] then
        return MESSAGES[status]
    end
    return DEFAULT_MESSAGE
end

function _M.serve(status)
    -- error_page =CODE preserves ngx.status; do not override it in Lua.
    status = tonumber(ngx.status) or tonumber(status) or 502
    local message = _M.message_for(status)
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
