-- Per-site request counters (access phase). Unmatched requests are not recorded.
-- Worker-0 tick syncs each site to Redis and publishes a snapshot whose
-- ``global`` block is the dynamic sum of configured sites (not stored separately).
-- Live windows (10s–60m) are sliding per-second sums; 24h uses per-site minute rings.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"

local _M = {}

local dict = ngx.shared.waf_traffic
local WINDOWS = { 10, 30, 60, 300, 1800, 3600 }
local DAY_SEC = 86400
local BUCKET_TTL = 3700
local SEC_REDIS_TTL = 3700
local MINUTE_KEEP = 1440
local SNAPSHOT_KEY = "waf:traffic:snapshot"
local VIEWER_KEY = "waf:logs:viewer_active"
local SEC_KEY_S = "waf:traffic:sec:s:"
local MIN_KEY_S = "waf:traffic:min:s:"
local ORIGIN_SEC_KEY_S = "waf:traffic:sec:o:"
local ORIGIN_MIN_KEY_S = "waf:traffic:min:o:"
local TRACKED_SITES_KEY = "tracked_site_ids"

local function bucket_key(site_id, sec)
    return "s:" .. tostring(site_id) .. ":" .. tostring(sec)
end

local function origin_bucket_key(site_id, sec)
    return "o:" .. tostring(site_id) .. ":" .. tostring(sec)
end

local function sum_window(prefix, now, window_sec)
    local total = 0
    for i = 0, window_sec - 1 do
        local v = dict:get(prefix .. tostring(now - i))
        if v then total = total + v end
    end
    return total
end

local function window_counts(now, site_id, prefix)
    prefix = prefix or ("s:" .. tostring(site_id) .. ":")
    local out = {}
    for _, w in ipairs(WINDOWS) do
        out[tostring(w)] = sum_window(prefix, now, w)
    end
    return out
end

local function empty_counts()
    local out = {}
    for _, w in ipairs(WINDOWS) do
        out[tostring(w)] = 0
    end
    return out
end

local function add_counts(dst, src)
    for _, w in ipairs(WINDOWS) do
        local key = tostring(w)
        dst[key] = (dst[key] or 0) + (src[key] or 0)
    end
    return dst
end

local function cache_global_windows(counts, day_total, cache_prefix)
    cache_prefix = cache_prefix or "wc:"
    for _, w in ipairs(WINDOWS) do
        local key = tostring(w)
        dict:set(cache_prefix .. key, counts[key] or 0, 120)
    end
    dict:set(cache_prefix .. "86400", day_total or 0, 120)
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

local function tracked_site_ids()
    if not dict then return {} end
    local raw = dict:get(TRACKED_SITES_KEY)
    if not raw or raw == "" then return {} end
    local parsed = cjson.decode(raw)
    if type(parsed) ~= "table" then return {} end
    return parsed
end

local function set_tracked_site_ids(ids)
    if not dict then return end
    dict:set(TRACKED_SITES_KEY, cjson.encode(ids) or "[]", 120)
end

function _M.get_global_count(window_sec)
    if not dict then return 0 end
    local w = tonumber(window_sec) or 0
    if w <= 0 then return 0 end
    if w == DAY_SEC then
        return tonumber(dict:get("wc:86400")) or 0
    end
    local cached = dict:get("wc:" .. tostring(w))
    if cached ~= nil then
        return cached
    end
    local now = math.floor(ngx.now())
    local total = 0
    for _, sid in ipairs(tracked_site_ids()) do
        total = total + sum_window("s:" .. tostring(sid) .. ":", now, w)
    end
    return total
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

function _M.get_global_origin_count(window_sec)
    if not dict then return 0 end
    local w = tonumber(window_sec) or 0
    if w <= 0 then return 0 end
    if w == DAY_SEC then
        return tonumber(dict:get("wc:o:86400")) or 0
    end
    local cached = dict:get("wc:o:" .. tostring(w))
    if cached ~= nil then
        return cached
    end
    local now = math.floor(ngx.now())
    local total = 0
    for _, sid in ipairs(tracked_site_ids()) do
        total = total + sum_window("o:" .. tostring(sid) .. ":", now, w)
    end
    return total
end

function _M.get_site_origin_count(site_id, window_sec)
    if not dict or site_id == nil then return 0 end
    local sid = tonumber(site_id)
    if not sid then return 0 end
    local w = tonumber(window_sec) or 0
    if w <= 0 then return 0 end
    if w == DAY_SEC then
        return tonumber(dict:get("wc:o:s:" .. tostring(sid) .. ":86400")) or 0
    end
    local now = math.floor(ngx.now())
    return sum_window("o:" .. tostring(sid) .. ":", now, w)
end

-- Only matched sites are counted; no global / unassigned bucket.
function _M.inc(site_id)
    if not dict then return end
    local sid = tonumber(site_id)
    if not sid then return end
    local now = math.floor(ngx.now())
    dict:incr(bucket_key(sid, now), 1, 0, BUCKET_TTL)
end

-- Origin requests: counted after WAF passes (proxied to upstream, not blocked).
function _M.inc_origin(site_id)
    if not dict then return end
    local sid = tonumber(site_id)
    if not sid then return end
    local now = math.floor(ngx.now())
    dict:incr(origin_bucket_key(sid, now), 1, 0, BUCKET_TTL)
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
    return SEC_KEY_S .. tostring(site_id) .. ":" .. tostring(sec)
end

local function redis_origin_sec_key(site_id, sec)
    return ORIGIN_SEC_KEY_S .. tostring(site_id) .. ":" .. tostring(sec)
end

local function redis_min_key(site_id)
    return MIN_KEY_S .. tostring(site_id)
end

local function redis_origin_min_key(site_id)
    return ORIGIN_MIN_KEY_S .. tostring(site_id)
end

local function sum_day_from_hash(red, min_key, now_min)
    local all = red:hgetall(min_key)
    if not all or all == ngx.null then
        return 0
    end
    local total = 0
    local cutoff = now_min - (MINUTE_KEEP - 1) * 60
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

local function shared_has_minute(prefix, minute_start, now)
    for sec = minute_start, now do
        if dict:get(prefix .. tostring(sec)) then
            return true
        end
    end
    return false
end

local function sync_site_to_redis(red, now, site_id, kind)
    local prefix = (kind == "origin") and ("o:" .. tostring(site_id) .. ":") or ("s:" .. tostring(site_id) .. ":")
    local sec_key_fn = (kind == "origin") and redis_origin_sec_key or redis_sec_key
    local min_key = (kind == "origin") and redis_origin_min_key(site_id) or redis_min_key(site_id)
    local day_cache_key = (kind == "origin")
        and ("wc:o:s:" .. tostring(site_id) .. ":86400")
        or ("wc:s:" .. tostring(site_id) .. ":86400")

    local sec_val = tonumber(dict:get(prefix .. tostring(now))) or 0
    red:set(sec_key_fn(site_id, now), sec_val, "EX", SEC_REDIS_TTL)

    local minute_start = now - (now % 60)
    local min_count = minute_sum(prefix, now, minute_start)
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
    dict:set(day_cache_key, day_total, 120)
    return day_total
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

local function configured_site_ids(cfg)
    local ids = {}
    local seen = {}
    if cfg and cfg.sites then
        for _, site in pairs(cfg.sites) do
            local sid = tonumber(site.id)
            if sid and not seen[sid] then
                seen[sid] = true
                ids[#ids + 1] = sid
            end
        end
    end
    table.sort(ids)
    return ids
end

local function hydrate_sec_keys(red, match_prefix, key_pattern, set_bucket_fn, seen, site_ids)
    local loaded = 0
    local cursor = "0"
    repeat
        local res = red:scan(cursor, "MATCH", match_prefix .. "*", "COUNT", 200)
        if not res or res == ngx.null then
            break
        end
        cursor = tostring(res[1])
        local keys = res[2] or {}
        for _, key in ipairs(keys) do
            local sid, sec = string.match(key, key_pattern)
            if sid and sec then
                local val = red:get(key)
                if val and val ~= ngx.null then
                    local n = tonumber(val)
                    if n and n > 0 then
                        local site_id = tonumber(sid)
                        set_bucket_fn(site_id, tonumber(sec), n)
                        loaded = loaded + 1
                        if site_id and not seen[site_id] then
                            seen[site_id] = true
                            site_ids[#site_ids + 1] = site_id
                        end
                    end
                end
            end
        end
    until cursor == "0"
    return loaded
end

local function hydrate_min_keys(red, match_prefix, key_pattern, day_cache_fmt, seen, site_ids)
    local day_total = 0
    local now = math.floor(ngx.now())
    local now_min = now - (now % 60)
    local cursor = "0"
    repeat
        local res = red:scan(cursor, "MATCH", match_prefix .. "*", "COUNT", 50)
        if not res or res == ngx.null then
            break
        end
        cursor = tostring(res[1])
        local keys = res[2] or {}
        for _, key in ipairs(keys) do
            local sid = string.match(key, key_pattern)
            if sid then
                local day_s = sum_day_from_hash(red, key, now_min)
                dict:set(string.format(day_cache_fmt, sid), day_s, 120)
                day_total = day_total + day_s
                local site_id = tonumber(sid)
                if site_id and not seen[site_id] then
                    seen[site_id] = true
                    site_ids[#site_ids + 1] = site_id
                end
            end
        end
    until cursor == "0"
    return day_total
end

--- Load per-site Redis second buckets into ngx.shared after process restart.
function _M.hydrate_from_redis()
    if not dict or ngx.worker.id() ~= 0 then
        return
    end
    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.WARN, "waf traffic: hydrate redis connect failed: ", err)
        return
    end

    local site_ids = {}
    local seen = {}

    local loaded_req = hydrate_sec_keys(
        red,
        SEC_KEY_S,
        "^waf:traffic:sec:s:(%d+):(%d+)$",
        function(site_id, sec, n)
            dict:set(bucket_key(site_id, sec), n, BUCKET_TTL)
        end,
        seen,
        site_ids
    )
    local loaded_origin = hydrate_sec_keys(
        red,
        ORIGIN_SEC_KEY_S,
        "^waf:traffic:sec:o:(%d+):(%d+)$",
        function(site_id, sec, n)
            dict:set(origin_bucket_key(site_id, sec), n, BUCKET_TTL)
        end,
        seen,
        site_ids
    )

    local day_total = hydrate_min_keys(
        red,
        MIN_KEY_S,
        "^waf:traffic:min:s:(%d+)$",
        "wc:s:%s:86400",
        seen,
        site_ids
    )
    local origin_day_total = hydrate_min_keys(
        red,
        ORIGIN_MIN_KEY_S,
        "^waf:traffic:min:o:(%d+)$",
        "wc:o:s:%s:86400",
        seen,
        site_ids
    )

    table.sort(site_ids)
    set_tracked_site_ids(site_ids)
    dict:set("wc:86400", day_total, 120)
    dict:set("wc:o:86400", origin_day_total, 120)

    rc.release(red)
    ngx.log(ngx.INFO, "waf traffic: hydrated req=", loaded_req, " origin=", loaded_origin,
        " day_sum=", day_total, " origin_day_sum=", origin_day_total)
end

function _M.tick(cfg)
    if not dict then return end
    if ngx.worker.id() ~= 0 then
        return
    end

    local now = math.floor(ngx.now())
    local thresholds, logging = thresholds_from_settings(cfg)
    refresh_viewer_flag()

    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.ERR, "waf traffic: redis connect failed: ", err)
        return
    end

    local site_ids = configured_site_ids(cfg)
    set_tracked_site_ids(site_ids)

    local global_counts = empty_counts()
    local origin_global_counts = empty_counts()
    local day_g = 0
    local origin_day_g = 0
    local sites_out = {}

    for _, sid in ipairs(site_ids) do
        local counts = window_counts(now, sid)
        local origin_counts = window_counts(now, sid, "o:" .. tostring(sid) .. ":")
        local day_s = sync_site_to_redis(red, now, sid)
        local origin_day_s = sync_site_to_redis(red, now, sid, "origin")
        add_counts(global_counts, counts)
        add_counts(origin_global_counts, origin_counts)
        day_g = day_g + (day_s or 0)
        origin_day_g = origin_day_g + (origin_day_s or 0)
        sites_out[tostring(sid)] = {
            windows = windows_payload(counts, day_s, nil, false),
            origin_windows = windows_payload(origin_counts, origin_day_s, nil, false),
        }
    end

    cache_global_windows(global_counts, day_g)
    cache_global_windows(origin_global_counts, origin_day_g, "wc:o:")
    local burst = update_burst(global_counts, logging)
    local windows_out = windows_payload(global_counts, day_g, thresholds, true)
    local origin_windows_out = windows_payload(origin_global_counts, origin_day_g, nil, false)

    local payload = cjson.encode({
        updated_at = now,
        global = {
            windows = windows_out,
            origin_windows = origin_windows_out,
            burst_active = burst,
        },
        sites = sites_out,
    })
    if payload then
        red:set(SNAPSHOT_KEY, payload, "EX", 120)
    end
    rc.release(red)
end

return _M
