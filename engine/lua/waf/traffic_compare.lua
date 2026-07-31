-- Match traffic.global / traffic.site rule conditions against live counters + baselines.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"
local traffic_counter = require "waf.traffic_counter"

local _M = {}

local BASELINE_KEY = "waf:traffic:baselines"
local CACHE_TTL = 60
local BASELINE_MIN_WINDOW = 300
local cache = { data = nil, at = 0 }

local function baselines_payload()
    local now = ngx.time()
    if cache.data and (now - cache.at) < CACHE_TTL then
        return cache.data
    end
    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.ERR, "waf traffic_compare: redis connect failed: ", err)
        return cache.data
    end
    local raw = red:get(BASELINE_KEY)
    rc.release(red)
    if not raw or raw == ngx.null then
        return nil
    end
    local parsed = cjson.decode(raw)
    if parsed then
        cache.data = parsed
        cache.at = now
        return parsed
    end
    return nil
end

local function baseline_avg(scope, site_id, window_sec)
    local payload = baselines_payload()
    if not payload then return nil end
    local key = tostring(window_sec)
    if scope == "site" then
        if not site_id then return nil end
        local sites = payload.sites or {}
        local site_item = sites[tostring(site_id)]
        if not site_item then return nil end
        local item = site_item[key]
        if not item then return nil end
        return tonumber(item.avg)
    end
    -- Global baseline = sum of per-site baselines for the same window (not stored).
    local sites = payload.sites or {}
    local total = 0
    local any = false
    for _, site_item in pairs(sites) do
        if type(site_item) == "table" then
            local item = site_item[key]
            local avg = item and tonumber(item.avg) or nil
            if avg and avg > 0 then
                total = total + avg
                any = true
            end
        end
    end
    if not any then return nil end
    return total
end

local function current_count(scope, site_id, window_sec)
    if scope == "origin_site" then
        return traffic_counter.get_site_origin_count(site_id, window_sec)
    end
    if scope == "origin_global" then
        return traffic_counter.get_global_origin_count(window_sec)
    end
    if scope == "site" then
        return traffic_counter.get_site_count(site_id, window_sec)
    end
    return traffic_counter.get_global_count(window_sec)
end

local function current_qps(scope, site_id, window_sec)
    local w = tonumber(window_sec) or 0
    if w <= 0 then return 0 end
    return current_count(scope, site_id, w) / w
end

function _M.match(value, scope, site_id)
    if type(value) ~= "table" then return false end
    scope = scope or "global"

    local window_sec = tonumber(value.window_sec)
    local compare = value.compare
    if not window_sec or not compare then return false end

    local current = current_count(scope, site_id, window_sec)

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
    if compare == "qps_gt" then
        local threshold = tonumber(value.threshold)
        if not threshold then return false end
        return current_qps(scope, site_id, window_sec) > threshold
    end
    if compare == "qps_lt" then
        local threshold = tonumber(value.threshold)
        if not threshold then return false end
        return current_qps(scope, site_id, window_sec) < threshold
    end

    if scope == "origin_global" or scope == "origin_site" then
        return false
    end

    if window_sec < BASELINE_MIN_WINDOW then
        return false
    end

    local baseline = baseline_avg(scope, site_id, window_sec)
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
