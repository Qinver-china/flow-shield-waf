-- Rate limiting based on lua-resty-limit-traffic (fixed window / count) backed
-- by the waf_ratelimit shared dict. Key is composed from the configured
-- catalog fields so limits can be per-IP, per-URI, per-cookie, etc.
local limit_count = require "resty.limit.count"

local _M = {}

local DICT = "waf_ratelimit"
local lim_cache = {}

local function build_key(rl, ext)
    local parts = { "rl", tostring(rl.id) }
    for _, k in ipairs(rl.keys or {}) do
        local field = k.field or k
        local arg = k.arg
        local v = ext:get(field, arg)
        parts[#parts + 1] = tostring(v or "-")
    end
    return table.concat(parts, ":")
end

local function fail_open_enabled(cfg)
    local settings = cfg and cfg.settings or {}
    if settings.ratelimit_fail_open == false then
        return false
    end
    return true
end

-- Returns true if this request EXCEEDS the limit (should be acted on).
function _M.exceeded(rl, ext, cfg)
    local window = tonumber(rl.window) or 60
    local threshold = tonumber(rl.threshold) or 100
    local cache_key = table.concat({ tostring(rl.id), window, threshold }, ":")
    local lim = lim_cache[cache_key]
    if not lim then
        local err
        lim, err = limit_count.new(DICT, threshold, window)
        if not lim then
            ngx.log(ngx.ERR, "waf ratelimit: new failed: ", err)
            return not fail_open_enabled(cfg)
        end
        lim_cache[cache_key] = lim
    end
    local key = build_key(rl, ext)
    local delay, err = lim:incoming(key, true)
    if not delay then
        if err == "rejected" then
            return true
        end
        if err then
            ngx.log(ngx.ERR, "waf ratelimit: incoming error: ", err)
        end
        return not fail_open_enabled(cfg)
    end
    return false
end

return _M
