-- Match traffic.global rule conditions against live counters + Redis baselines.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"
local traffic_counter = require "waf.traffic_counter"

local _M = {}

local BASELINE_KEY = "waf:traffic:baselines"
local CACHE_TTL = 60
local cache = { data = nil, at = 0 }

local function baselines_global()
    local now = ngx.time()
    if cache.data and (now - cache.at) < CACHE_TTL then
        return cache.data
    end
    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.WARN, "waf traffic_compare: redis connect failed: ", err)
        return cache.data
    end
    local raw = red:get(BASELINE_KEY)
    rc.release(red)
    if not raw or raw == ngx.null then
        return nil
    end
    local parsed = cjson.decode(raw)
    if parsed and parsed.global then
        cache.data = parsed.global
        cache.at = now
        return cache.data
    end
    return nil
end

local function baseline_avg(window_sec)
    local global = baselines_global()
    if not global then return nil end
    local item = global[tostring(window_sec)]
    if not item then return nil end
    return tonumber(item.avg)
end

function _M.match(value)
    if type(value) ~= "table" then return false end

    local window_sec = tonumber(value.window_sec)
    local compare = value.compare
    if not window_sec or not compare then return false end

    local current = traffic_counter.get_global_count(window_sec)

    if compare == "abs_gt" then
        local threshold = tonumber(value.threshold)
        if not threshold then return false end
        return current > threshold
    end
    if compare == "abs_lt" then
        local threshold = tonumber(value.threshold)
        if not threshold then return false end
        return current < threshold
    end

    if window_sec < 300 then
        return false
    end

    local baseline = baseline_avg(window_sec)
    if not baseline or baseline <= 0 then
        return false
    end

    local percent = tonumber(value.percent) or 0
    if compare == "baseline_gt" then
        return current > baseline * (1 + percent / 100)
    end
    if compare == "baseline_lt" then
        return current < baseline * (1 - percent / 100)
    end

    return false
end

return _M
