-- Block action: return an interception page and stop the request.
local page_render = require "waf.page_render"

local _M = {}

function _M.run(cfg, site, ctx, meta)
    local status, html = page_render.render_block_page(cfg, site, ctx, meta)
    ngx.status = status
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["X-WAF-Block"] = ctx.request_id or "1"
    ngx.say(html)
    return ngx.exit(status)
end

return _M
