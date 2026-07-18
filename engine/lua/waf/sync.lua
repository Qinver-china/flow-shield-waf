-- Pull WAF config from Redis and cache it in worker-local memory.
-- The backend is the source of truth: it writes `waf:config` (JSON) and
-- bumps `waf:config:version` on every change. Workers poll the version.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"
local rule_sort = require "waf.rule_sort"

local _M = {}

local VERSION_KEY = "waf:config:version"
local CONFIG_KEY = "waf:config"

local _backoff_until = 0
local _fail_streak = 0

local function default_logging_settings()
    return {
        logging_control_mode = "manual",
        logging_enabled = true,
        logging_skip_observe = false,
        observe_sample_rate_idle = 0.01,
        observe_sample_rate_active = 1.0,
        logging_detail_on_block = true,
        logging_auto_cooldown_sec = 120,
        logging_auto_observe_sample_rate = 1.0,
        logging_auto_thresholds = {
            { window_sec = 10, max_requests = 500 },
            { window_sec = 30, max_requests = 1200 },
            { window_sec = 60, max_requests = 2000 },
            { window_sec = 300, max_requests = 8000 },
            { window_sec = 1800, max_requests = 40000 },
            { window_sec = 3600, max_requests = 80000 },
        },
    }
end

local function empty_config()
    return {
        version = -1,
        sites = {},
        rules = {},
        whitelist = {},
        blacklist = {},
        exceptions = {},
        ratelimits = {},
        ip_groups = {},
        settings = {
            js_challenge_ttl = 1800,
            captcha_ttl = 1800,
            clearance_fingerprint_dims = { "ip", "ua" },
            debug_mode = false,
            ratelimit_fail_open = true,
            logging = default_logging_settings(),
        },
    }
end

-- worker-local cache
local _config = empty_config()

local function index_by_domain(sites)
    local map = {}
    for _, s in ipairs(sites or {}) do
        local domains = s.domains
        if type(domains) ~= "table" or #domains == 0 then
            domains = s.domain and { s.domain } or {}
        end
        for _, d in ipairs(domains) do
            if d and d ~= "" then
                map[d] = s
            end
        end
    end
    return map
end

local function sort_by_priority(items)
    table.sort(items or {}, function(a, b)
        return (a.priority or 100) < (b.priority or 100)
    end)
    return items
end

local function sort_rules(items)
    return rule_sort.sort_rules(items)
end

local function mark_failure()
    _fail_streak = _fail_streak + 1
    local delay = math.min(30, 2 ^ math.min(_fail_streak, 5))
    _backoff_until = ngx.now() + delay
end

local function has_cached_config()
    return (_config.version or -1) >= 0
end

function _M.load(force)
    local now = ngx.now()
    if not force and has_cached_config() and now < _backoff_until then
        return true
    end

    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.ERR, "waf sync: redis connect failed: ", err)
        mark_failure()
        return has_cached_config()
    end

    local ver, verr = red:get(VERSION_KEY)
    if ver == nil then
        rc.release(red)
        ngx.log(ngx.WARN, "waf sync: get version failed: ", verr)
        mark_failure()
        return has_cached_config()
    end
    if ver == ngx.null then
        ver = "0"
    end
    ver = tonumber(ver) or 0

    if not force and ver == _config.version then
        rc.release(red)
        return true
    end

    local raw, rerr = red:get(CONFIG_KEY)
    rc.release(red)
    if raw == nil or raw == ngx.null then
        ngx.log(ngx.WARN, "waf sync: get config failed or empty: ", rerr)
        mark_failure()
        return has_cached_config()
    end

    local parsed = cjson.decode(raw)
    if not parsed then
        ngx.log(ngx.ERR, "waf sync: config json decode failed")
        mark_failure()
        return has_cached_config()
    end

    _config = {
        version = ver,
        sites = index_by_domain(parsed.sites),
        rules = sort_rules(parsed.rules or {}),
        whitelist = parsed.whitelist or {},
        blacklist = parsed.blacklist or {},
        exceptions = parsed.exceptions or {},
        ratelimits = sort_by_priority(parsed.ratelimits or {}),
        ip_groups = parsed.ip_groups or {},
        settings = parsed.settings or {
            js_challenge_ttl = 1800,
            captcha_ttl = 1800,
            clearance_fingerprint_dims = { "ip", "ua" },
            debug_mode = false,
            ratelimit_fail_open = true,
            logging = default_logging_settings(),
        },
    }
    _fail_streak = 0
    _backoff_until = 0
    ngx.log(ngx.NOTICE, "waf sync: loaded config version ", ver, " rules=", #_config.rules)
    return true
end

function _M.get()
    return _config
end

function _M.needs_load()
    return (_config.version or -1) < 0
end

function _M.site_by_domain(domain)
    return _config.sites[domain]
end

return _M
