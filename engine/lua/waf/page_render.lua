-- Resolve and render custom block pages / captcha footers.
local util = require "waf.util"

local _M = {}

local DEFAULT_BLOCK_STATUS = 403

local DEFAULT_BLOCK_HTML = [[<!DOCTYPE html>
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
.brand b,.brand a,h2 a{color:#38bdf8}
.brand a,h2 a{text-decoration:none}
.brand a:hover,h2 a:hover{text-decoration:underline}
</style></head>
<body><div class="box">
<h1>403</h1>
<h2>请求被<a href="https://fswaf.top" target="_blank" rel="noopener noreferrer">流盾WAF</a> 拦截</h2>
<p>您的请求命中了防护规则，已被阻止。若您认为这是误判，请联系站点管理员。</p>
<div class="rid">Request ID: {request_id}</div>
<div class="brand">由 <a href="https://fswaf.top" target="_blank" rel="noopener noreferrer"><b>流盾WAF</b></a> · Flow Shield WAF 提供防护</div>
</div></body></html>]]

local DEFAULT_CAPTCHA_FOOTER = '由 <a href="https://fswaf.top" target="_blank" rel="noopener noreferrer"><b>流盾WAF</b></a> · Flow Shield WAF 提供防护'

local function pick_site_override(site, key)
    if not site or type(site) ~= "table" then
        return nil
    end
    local cfg = site[key]
    if type(cfg) ~= "table" or cfg.enabled ~= true then
        return nil
    end
    return cfg
end

function _M.template_vars(ctx, meta)
    meta = meta or {}
    return {
        request_id = ctx.request_id or "",
        client_ip = util.client_ip(),
        domain = ctx.domain or ngx.var.host or "",
        method = ngx.req.get_method() or "",
        uri = ngx.var.request_uri or ngx.var.uri or "",
        rule_id = tostring(meta.id or ""),
        rule_name = meta.name or "",
        source = meta.source or "",
    }
end

function _M.render(html, vars)
    if type(html) ~= "string" or html == "" then
        return html
    end
    local out = html
    for key, value in pairs(vars or {}) do
        out = out:gsub("{" .. key .. "}", tostring(value or ""))
    end
    return out
end

local function pick_meta_override(meta, key)
    if not meta or type(meta) ~= "table" then
        return nil
    end
    local cfg = meta[key]
    if type(cfg) ~= "table" or cfg.enabled ~= true then
        return nil
    end
    return cfg
end

function _M.resolve_block_page(cfg, site, meta)
    local override = pick_meta_override(meta, "block_page")
    if override then
        return {
            status_code = tonumber(override.status_code) or DEFAULT_BLOCK_STATUS,
            html = override.html or DEFAULT_BLOCK_HTML,
        }
    end
    override = pick_site_override(site, "block_page")
    if override then
        return {
            status_code = tonumber(override.status_code) or DEFAULT_BLOCK_STATUS,
            html = override.html or DEFAULT_BLOCK_HTML,
        }
    end
    local global_cfg = (cfg and cfg.settings and cfg.settings.block_page) or {}
    return {
        status_code = tonumber(global_cfg.status_code) or DEFAULT_BLOCK_STATUS,
        html = global_cfg.html or DEFAULT_BLOCK_HTML,
    }
end

function _M.resolve_captcha_footer(cfg, site)
    local override = pick_site_override(site, "captcha_footer")
    if override and type(override.html) == "string" and override.html ~= "" then
        return override.html
    end
    local global_cfg = (cfg and cfg.settings and cfg.settings.captcha_footer) or {}
    if type(global_cfg.html) == "string" and global_cfg.html ~= "" then
        return global_cfg.html
    end
    return DEFAULT_CAPTCHA_FOOTER
end

function _M.render_block_page(cfg, site, ctx, meta)
    local page = _M.resolve_block_page(cfg, site, meta)
    local html = _M.render(page.html, _M.template_vars(ctx, meta))
    return page.status_code, html
end

function _M.render_captcha_footer(cfg, site, ctx, meta)
    local footer = _M.resolve_captcha_footer(cfg, site)
    return _M.render(footer, _M.template_vars(ctx, meta))
end

return _M
