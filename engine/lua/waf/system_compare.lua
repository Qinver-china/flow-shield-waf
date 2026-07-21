-- Match system.cpu rule conditions against Redis rolling CPU/load averages.
-- Hot-path design:
--   * only runs when a rule leaf uses system.cpu (zero cost otherwise)
--   * worker-local parsed cache + ngx.shared raw cache (cross-worker)
--   * short Redis timeouts; negative cache to avoid stampede when key missing
--   * 1/5/30-minute averages tolerate a few seconds of staleness
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"

local _M = {}

local SNAPSHOT_KEY = "waf:system:metrics"
local SHARED_RAW_KEY = "system_metrics:raw"
local SHARED_AT_KEY = "system_metrics:at"
-- Align with sample interval; window averages are 60s+ so 5s is fine.
local CACHE_TTL = 5
local NEGATIVE_CACHE_TTL = 2
local REDIS_TIMEOUT_MS = 50

local METRIC_BY_COMPARE = {
    container_cpu_gt = "container_cpu_pct_avg",
    container_cpu_lt = "container_cpu_pct_avg",
    host_cpu_gt = "host_cpu_pct_avg",
    host_cpu_lt = "host_cpu_pct_avg",
}

-- Per-nginx-worker parsed cache (avoids cjson.decode on every request).
local cache = { data = nil, at = 0, negative = false }

local function shared_dict()
    return ngx.shared.waf_config
end

local function read_shared(now)
    local dict = shared_dict()
    if not dict then
        return nil, false
    end
    local at = dict:get(SHARED_AT_KEY)
    if not at or (now - at) >= CACHE_TTL then
        return nil, false
    end
    local raw = dict:get(SHARED_RAW_KEY)
    if raw == nil then
        return nil, false
    end
    if raw == "" then
        return nil, true -- negative hit
    end
    return raw, false
end

local function write_shared(raw, now, ttl)
    local dict = shared_dict()
    if not dict then
        return
    end
    ttl = ttl or CACHE_TTL
    -- Keep a little longer than logical TTL so late workers still see it.
    dict:set(SHARED_RAW_KEY, raw or "", ttl + 1)
    dict:set(SHARED_AT_KEY, now, ttl + 1)
end

local function fetch_redis_raw()
    local red, err = rc.connect()
    if not red then
        return nil, err
    end
    -- Keep WAF request path from blocking on a slow Redis.
    red:set_timeouts(REDIS_TIMEOUT_MS, REDIS_TIMEOUT_MS, REDIS_TIMEOUT_MS)
    local raw, gerr = red:get(SNAPSHOT_KEY)
    rc.release(red)
    if gerr then
        return nil, gerr
    end
    if not raw or raw == ngx.null then
        return nil, nil
    end
    return raw, nil
end

local function snapshot_payload()
    local now = ngx.time()
    if cache.at > 0 then
        local age = now - cache.at
        if cache.negative then
            if age < NEGATIVE_CACHE_TTL then
                return nil
            end
        elseif cache.data and age < CACHE_TTL then
            return cache.data
        end
    end

    local raw, negative = read_shared(now)
    if negative then
        cache.data = nil
        cache.negative = true
        cache.at = now
        return nil
    end

    if not raw then
        local err
        raw, err = fetch_redis_raw()
        if err then
            ngx.log(ngx.ERR, "waf system_compare: redis get failed: ", err)
            -- Prefer stale local/shared data over blocking or failing closed hard.
            if cache.data and not cache.negative then
                -- Hold stale briefly so workers do not stampede Redis on outage.
                cache.at = now
                return cache.data
            end
            local stale = shared_dict() and shared_dict():get(SHARED_RAW_KEY)
            if stale and stale ~= "" then
                local parsed = cjson.decode(stale)
                if parsed then
                    cache.data = parsed
                    cache.negative = false
                    cache.at = now
                    return parsed
                end
            end
            cache.data = nil
            cache.negative = true
            cache.at = now
            write_shared("", now, NEGATIVE_CACHE_TTL)
            return nil
        end
        if not raw then
            cache.data = nil
            cache.negative = true
            cache.at = now
            write_shared("", now, NEGATIVE_CACHE_TTL)
            return nil
        end
        write_shared(raw, now, CACHE_TTL)
    end

    local parsed = cjson.decode(raw)
    if not parsed then
        cache.data = nil
        cache.negative = true
        cache.at = now
        return nil
    end
    cache.data = parsed
    cache.negative = false
    cache.at = now
    return parsed
end

local function current_value(window_sec, metric_key)
    local payload = snapshot_payload()
    if not payload then
        return nil
    end
    local windows = payload.windows or {}
    local row = windows[tostring(window_sec)]
    if type(row) ~= "table" then
        return nil
    end
    return tonumber(row[metric_key])
end

function _M.match(value)
    if type(value) ~= "table" then
        return false
    end
    local window_sec = tonumber(value.window_sec)
    local compare = value.compare
    local threshold = tonumber(value.threshold)
    if not window_sec or not compare or threshold == nil then
        return false
    end
    local metric_key = METRIC_BY_COMPARE[compare]
    if not metric_key then
        return false
    end
    local current = current_value(window_sec, metric_key)
    if current == nil then
        return false
    end

    if compare:sub(-3) == "_gt" then
        return current > threshold
    end
    if compare:sub(-3) == "_lt" then
        return current < threshold
    end
    return false
end

return _M
