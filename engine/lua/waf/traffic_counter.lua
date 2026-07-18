-- Per-second request counters (all requests through access phase).
-- Aggregation + burst detection run in a 1s timer, not on the request path.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"

local _M = {}

local dict = ngx.shared.waf_traffic
local WINDOWS = { 10, 30, 60, 300, 1800, 3600 }
local BUCKET_TTL = 3700
local SNAPSHOT_KEY = "waf:traffic:snapshot"
local VIEWER_KEY = "waf:logs:viewer_active"

local function bucket_key(site_id, sec)
    if site_id then
        return "s:" .. tostring(site_id) .. ":" .. tostring(sec)
    end
    return "g:" .. tostring(sec)
end

local function sum_window(prefix, now, window_sec)
    local total = 0
    for i = 0, window_sec - 1 do
        local v = dict:get(prefix .. tostring(now - i))
        if v then total = total + v end
    end
    return total
end

local function window_counts(now, site_id)
    local prefix = site_id and ("s:" .. tostring(site_id) .. ":") or "g:"
    local out = {}
    for _, w in ipairs(WINDOWS) do
        out[tostring(w)] = sum_window(prefix, now, w)
    end
    return out
end

local function cache_global_windows(counts)
    for _, w in ipairs(WINDOWS) do
        local key = tostring(w)
        dict:set("wc:" .. key, counts[key] or 0, 120)
    end
end

function _M.get_global_count(window_sec)
    if not dict then return 0 end
    local w = tonumber(window_sec) or 0
    local cached = dict:get("wc:" .. tostring(w))
    if cached ~= nil then
        return cached
    end
    local now = math.floor(ngx.now())
    return sum_window("g:", now, w)
end

function _M.get_site_count(site_id, window_sec)
    if not dict or site_id == nil then return 0 end
    local sid = tonumber(site_id)
    if not sid then return 0 end
    local w = tonumber(window_sec) or 0
    if w <= 0 then return 0 end
    local now = math.floor(ngx.now())
    return sum_window("s:" .. tostring(sid) .. ":", now, w)
end

function _M.inc(site_id)
    if not dict then return end
    local now = math.floor(ngx.now())
    dict:incr(bucket_key(nil, now), 1, 0, BUCKET_TTL)
    if site_id then
        dict:incr(bucket_key(site_id, now), 1, 0, BUCKET_TTL)
    end
end

function _M.burst_active()
    return dict and (dict:get("burst_active") == 1) or false
end

function _M.viewer_active()
    return dict and (dict:get("viewer_active") == 1) or false
end

local function thresholds_from_settings(cfg)
    local logging = (cfg and cfg.settings and cfg.settings.logging) or {}
    local th = logging.logging_auto_thresholds
    if type(th) ~= "table" or #th == 0 then
        th = {
            { window_sec = 10, max_requests = 500 },
            { window_sec = 30, max_requests = 1200 },
            { window_sec = 60, max_requests = 2000 },
            { window_sec = 300, max_requests = 8000 },
            { window_sec = 1800, max_requests = 40000 },
            { window_sec = 3600, max_requests = 80000 },
        }
    end
    return th, logging
end

local function any_over_threshold(counts, thresholds)
    for _, item in ipairs(thresholds) do
        local w = tostring(item.window_sec or item.window)
        local max_r = tonumber(item.max_requests) or 0
        if max_r > 0 and (counts[w] or 0) > max_r then
            return true
        end
    end
    return false
end

local function all_under_threshold(counts, thresholds)
    for _, item in ipairs(thresholds) do
        local w = tostring(item.window_sec or item.window)
        local max_r = tonumber(item.max_requests) or 0
        if max_r > 0 and (counts[w] or 0) >= max_r then
            return false
        end
    end
    return true
end

local function update_burst(counts, logging)
    local mode = logging.logging_control_mode or "manual"
    if mode ~= "auto_by_traffic" then
        dict:set("burst_active", 0)
        dict:set("burst_below_since", 0)
        return false
    end

    local thresholds = logging.logging_auto_thresholds or {}
    local cooldown = tonumber(logging.logging_auto_cooldown_sec) or 120
    local latched = dict:get("burst_active") == 1
    local below_since = dict:get("burst_below_since") or 0
    local now = ngx.time()

    if any_over_threshold(counts, thresholds) then
        dict:set("burst_active", 1)
        dict:set("burst_below_since", 0)
        return true
    end

    if not latched then
        return false
    end

    if all_under_threshold(counts, thresholds) then
        if below_since == 0 then
            dict:set("burst_below_since", now)
            return true
        end
        if now - below_since >= cooldown then
            dict:set("burst_active", 0)
            dict:set("burst_below_since", 0)
            return false
        end
        return true
    end

    dict:set("burst_below_since", 0)
    return true
end

local function refresh_viewer_flag()
    local red, err = rc.connect()
    if not red then
        return
    end
    local val = red:get(VIEWER_KEY)
    rc.release(red)
    if val and val ~= ngx.null and val ~= "" then
        dict:set("viewer_active", 1, 60)
    else
        dict:set("viewer_active", 0, 60)
    end
end

function _M.tick(cfg)
    if not dict then return end

    local now = math.floor(ngx.now())
    local global_counts = window_counts(now, nil)
    cache_global_windows(global_counts)
    local thresholds, logging = thresholds_from_settings(cfg)
    local burst = update_burst(global_counts, logging)

    -- only worker 0 publishes snapshot and polls viewer flag
    if ngx.worker.id() ~= 0 then
        return
    end

    refresh_viewer_flag()

    local windows_out = {}
    for _, w in ipairs(WINDOWS) do
        local key = tostring(w)
        local requests = global_counts[key] or 0
        local th_val = nil
        for _, item in ipairs(thresholds) do
            if tonumber(item.window_sec) == w then
                th_val = tonumber(item.max_requests)
                break
            end
        end
        windows_out[#windows_out + 1] = {
            sec = w,
            requests = requests,
            qps = requests / w,
            threshold = th_val,
        }
    end

    local function site_windows_payload(counts)
        local out = {}
        for _, w in ipairs(WINDOWS) do
            local key = tostring(w)
            local requests = counts[key] or 0
            out[#out + 1] = {
                sec = w,
                requests = requests,
                qps = requests / w,
            }
        end
        return out
    end

    local sites_out = {}
    if cfg and cfg.sites then
        for _, site in pairs(cfg.sites) do
            local sid = tonumber(site.id)
            if sid then
                local counts = window_counts(now, sid)
                sites_out[tostring(sid)] = {
                    windows = site_windows_payload(counts),
                }
            end
        end
    end

    local payload = cjson.encode({
        updated_at = now,
        global = {
            windows = windows_out,
            burst_active = burst,
        },
        sites = sites_out,
    })
    if not payload then return end

    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.WARN, "waf traffic: redis connect failed: ", err)
        return
    end
    red:set(SNAPSHOT_KEY, payload, "EX", 10)
    rc.release(red)
end

return _M
