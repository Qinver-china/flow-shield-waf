-- Debug response headers (enabled via settings.debug_mode).
local _M = {}

local function safe_header(val)
    if val == nil then
        return ""
    end
    local s = tostring(val):gsub("[%c\r\n]", "")
    if #s > 512 then
        s = s:sub(1, 512)
    end
    if s == "" then
        return s
    end
    -- HTTP header values are ASCII-only; encode Unicode per RFC 5987 / RFC 8187.
    for i = 1, #s do
        local b = s:byte(i)
        if b < 32 or b > 126 then
            return "UTF-8''" .. ngx.escape_uri(s)
        end
    end
    return s
end

function _M.enabled(settings)
    settings = settings or {}
    return settings.debug_mode == true
end

function _M.apply(cfg, ctx, mode, meta)
    local settings = (cfg and cfg.settings) or {}
    if not _M.enabled(settings) then
        return
    end
    meta = meta or {}
    ctx = ctx or {}
    ngx.header["X-WAF-Debug"] = "1"
    ngx.header["X-WAF-Request-Id"] = safe_header(ctx.request_id)
    ngx.header["X-WAF-Mode"] = safe_header(mode)
    if meta.id ~= nil then
        ngx.header["X-WAF-Rule-Id"] = safe_header(meta.id)
    end
    if meta.name then
        ngx.header["X-WAF-Rule-Name"] = safe_header(meta.name)
    end
    if meta.source then
        ngx.header["X-WAF-Rule-Source"] = safe_header(meta.source)
    end
    if meta.type then
        ngx.header["X-WAF-Rule-Type"] = safe_header(meta.type)
    end
end

return _M
