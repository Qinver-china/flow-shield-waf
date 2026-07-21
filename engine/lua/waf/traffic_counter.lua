-- Per-second request counters (all requests through access phase).
-- Hot path uses ngx.shared; worker-0 tick syncs sec/min to Redis and publishes snapshot.
-- 24h windows use Redis minute rings (global + per-site); 10s is live-only (not DB-backed).
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"

local _M = {}

local dict = ngx.shared.waf_traffic
-- Live sliding windows (10s excluded from DB backup by design).
local WINDOWS = { 10, 30, 60, 300, 1800, 3600 }
local DAY_SEC = 86400
local BUCKET_TTL = 3700
local SEC_REDIS_TTL = 3700
local MINUTE_KEEP = 1440
local SNAPSHOT_KEY = "waf:traffic:snapshot"
local VIEWER_KEY = "waf:logs:viewer_active"
local SEC_KEY_G = "waf:traffic:sec:g:"
local SEC_KEY_S = "waf:traffic:sec:s:"
local MIN_KEY_G = "waf:traffic:min:g"
local MIN_KEY_S = "waf:traffic:min:s:"

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

local function minute_sum(prefix, now, minute_start)
    local total = 0
    local last = math.min(now, minute_start + 59)
    for sec = minute_start, last do
        local v = dict:get(prefix .. tostring(sec))
        if v then total = total + v end
    end
    return total
end

function _M.get_global_count(window_sec)
    if not dict then return 0 end
    local w = tonumber(window_sec) or 0
    if w == DAY_SEC then
        return tonumber(dict:get("wc:86400")) or 0
    end
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
    if w == DAY_SEC then
        return tonumber(dict:get("wc:s:" .. tostring(sid) .. ":86400")) or 0
    end
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

local function redis_sec_key(site_id, sec)
    if site_id then
        return SEC_KEY_S .. tostring(site_id) .. ":" .. tostring(sec)
    end
    return SEC_KEY_G .. tostring(sec)
end

local function redis_min_key(site_id)
    if site_id then
        return MIN_KEY_S .. tostring(site_id)
    end
    return MIN_KEY_G
end

-- Sum minute-hash fields within the last MINUTE_KEEP minutes.
local function sum_day_from_hash(red, min_key, now_min)
    local all = red:hgetall(min_key)
    if not all or all == ngx.null then
        return 0
    end
    local total = 0
    local cutoff = now_min - (MINUTE_KEEP - 1) * 60
    -- hgetall returns flat {k1,v1,k2,v2,...}
    for i = 1, #all, 2 do
        local m = tonumber(all[i])
        local v = tonumber(all[i + 1]) or 0
        if m and m >= cutoff and m <= now_min then
            total = total + v
        elseif m and m < cutoff then
            red:hdel(min_key, tostring(m))
        end
    end
    return total
end

-- Durable windows (>=1m): sum Redis minute ring (survives shared-dict wipe).
local function sum_minutes(red, min_key, now, window_sec)
    local minute_start = now - (now % 60)
    local need = math.ceil(window_sec / 60)
    local total = 0
    for i = 0, need - 1 do
        local m = minute_start - (i * 60)
        local v = red:hget(min_key, tostring(m))
        if v and v ~= ngx.null then
            total = total + (tonumber(v) or 0)
        end
    end
    return total
end

local function shared_has_minute(prefix, minute_start, now)
    for sec = minute_start, now do
        if dict:get(prefix .. tostring(sec)) then
            return true
        end
    end
    return false
end

local function sync_scope_to_redis(red, now, site_id, prefix)
    local sec_val = tonumber(dict:get(prefix .. tostring(now))) or 0
    red:set(redis_sec_key(site_id, now), sec_val, "EX", SEC_REDIS_TTL)

    local minute_start = now - (now % 60)
    local min_key = redis_min_key(site_id)
    local min_count = minute_sum(prefix, now, minute_start)
    -- After Redis restore, shared may be empty briefly — do not zero the restored minute.
    if shared_has_minute(prefix, minute_start, now) then
        red:hset(min_key, tostring(minute_start), min_count)
    else
        local existing = red:hget(min_key, tostring(minute_start))
        if existing and existing ~= ngx.null then
            min_count = tonumber(existing) or 0
        else
            red:hset(min_key, tostring(minute_start), min_count)
        end
    end

    local day_total = sum_day_from_hash(red, min_key, minute_start)
    if site_id then
        dict:set("wc:s:" .. tostring(site_id) .. ":86400", day_total, 120)
    else
        dict:set("wc:86400", day_total, 120)
    end
    return day_total, min_key
end

local function apply_durable_windows(red, counts, min_key, now)
    for _, w in ipairs(WINDOWS) do
        if w >= 60 then
            counts[tostring(w)] = sum_minutes(red, min_key, now, w)
        end
    end
end

local function windows_payload(counts, day_total, thresholds, with_threshold)
    local out = {}
    for _, w in ipairs(WINDOWS) do
        local key = tostring(w)
        local requests = counts[key] or 0
        local row = {
            sec = w,
            requests = requests,
            qps = requests / w,
        }
        if with_threshold and thresholds then
            for _, item in ipairs(thresholds) do
                if tonumber(item.window_sec) == w then
                    row.threshold = tonumber(item.max_requests)
                    break
                end
            end
        end
        out[#out + 1] = row
    end
    out[#out + 1] = {
        sec = DAY_SEC,
        requests = day_total or 0,
        qps = (day_total or 0) / DAY_SEC,
    }
    return out
end

--- Load Redis second buckets into ngx.shared after process restart.
function _M.hydrate_from_redis()
    if not dict or ngx.worker.id() ~= 0 then
        return
    end
    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.WARN, "waf traffic: hydrate redis connect failed: ", err)
        return
    end

    local now = math.floor(ngx.now())
    local loaded = 0
    for i = 0, BUCKET_TTL - 1 do
        local sec = now - i
        local gkey = redis_sec_key(nil, sec)
        local gval = red:get(gkey)
        if gval and gval ~= ngx.null then
            local n = tonumber(gval)
            if n and n > 0 then
                dict:set(bucket_key(nil, sec), n, BUCKET_TTL)
                loaded = loaded + 1
            end
        end
    end

    -- Per-site second buckets via SCAN
    local cursor = "0"
    repeat
        local res = red:scan(cursor, "MATCH", SEC_KEY_S .. "*", "COUNT", 200)
        if not res or res == ngx.null then
            break
        end
        cursor = tostring(res[1])
        local keys = res[2] or {}
        for _, key in ipairs(keys) do
            local sid, sec = string.match(key, "^waf:traffic:sec:s:(%d+):(%d+)$")
            if sid and sec then
                local val = red:get(key)
                if val and val ~= ngx.null then
                    local n = tonumber(val)
                    if n and n > 0 then
                        dict:set(bucket_key(tonumber(sid), tonumber(sec)), n, BUCKET_TTL)
                        loaded = loaded + 1
                    end
                end
            end
        end
    until cursor == "0"

    local now_min = now - (now % 60)
    local day_g = sum_day_from_hash(red, MIN_KEY_G, now_min)
    dict:set("wc:86400", day_g, 120)

    -- Per-site 24h caches from minute rings
    cursor = "0"
    repeat
        local res = red:scan(cursor, "MATCH", MIN_KEY_S .. "*", "COUNT", 50)
        if not res or res == ngx.null then
            break
        end
        cursor = tostring(res[1])
        local keys = res[2] or {}
        for _, key in ipairs(keys) do
            local sid = string.match(key, "^waf:traffic:min:s:(%d+)$")
            if sid then
                local day_s = sum_day_from_hash(red, key, now_min)
                dict:set("wc:s:" .. sid .. ":86400", day_s, 120)
            end
        end
    until cursor == "0"

    rc.release(red)
    ngx.log(ngx.INFO, "waf traffic: hydrated ", loaded, " sec buckets from redis; day_g=", day_g)
end

function _M.tick(cfg)
    if not dict then return end

    -- Heavy window aggregation + Redis publish only on worker 0.
    if ngx.worker.id() ~= 0 then
        return
    end

    local now = math.floor(ngx.now())
    local global_counts = window_counts(now, nil)
    local thresholds, logging = thresholds_from_settings(cfg)

    refresh_viewer_flag()

    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.ERR, "waf traffic: redis connect failed: ", err)
        return
    end

    local day_g, min_g = sync_scope_to_redis(red, now, nil, "g:")
    apply_durable_windows(red, global_counts, min_g, now)
    cache_global_windows(global_counts)
    local burst = update_burst(global_counts, logging)
    local windows_out = windows_payload(global_counts, day_g, thresholds, true)

    local sites_out = {}
    if cfg and cfg.sites then
        for _, site in pairs(cfg.sites) do
            local sid = tonumber(site.id)
            if sid then
                local counts = window_counts(now, sid)
                local prefix = "s:" .. tostring(sid) .. ":"
                local day_s, min_s = sync_scope_to_redis(red, now, sid, prefix)
                apply_durable_windows(red, counts, min_s, now)
                sites_out[tostring(sid)] = {
                    windows = windows_payload(counts, day_s, nil, false),
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
    if payload then
        -- Longer TTL: readers should not fall through to empty on brief stalls.
        red:set(SNAPSHOT_KEY, payload, "EX", 120)
    end
    rc.release(red)
end

return _M
