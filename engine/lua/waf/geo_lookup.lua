-- Geo field resolution shared by rule extractor and log emission.
-- Rule matching only reads geo when a geo.* field is evaluated (via extractor).
-- Log emission calls fill_entry after should_log passes: reuse trace values first,
-- then batch-read ngx.var geoip2_* only for fields still missing (lazy, log-path only).
-- Private (RFC1918 + loopback) client IPs skip all geo lookups — see util.is_private_ip.
local util = require "waf.util"

local _M = {}

local FIELDS = {
    { name = "country", entry = "geo_country", trace = "geo.country", var = "geoip2_country", fallback = "http_cf_ipcountry" },
    { name = "region", entry = "geo_region", trace = "geo.region", var = "geoip2_region" },
    { name = "city", entry = "geo_city", trace = "geo.city", var = "geoip2_city" },
    { name = "asn", entry = "geo_asn", trace = "geo.asn", var = "geoip2_asn", tonumber = true },
    { name = "isp", entry = "geo_isp", trace = "geo.isp", var = "geoip2_isp" },
}

local TRACE_BY_NAME = {}
for _, f in ipairs(FIELDS) do
    TRACE_BY_NAME[f.name] = f.trace
end

local function present(v)
    if v == nil then
        return false
    end
    if type(v) == "string" and v == "" then
        return false
    end
    return true
end

local function trace_pick(trace, field)
    if type(trace) ~= "table" then
        return nil
    end
    local item = trace[field]
    return item and item.value
end

local function cache_key(name)
    return "geo_" .. name
end

local EMPTY_VARS = {}

local function client_ip(extractor)
    if extractor and extractor.cache and extractor.cache.ip then
        return extractor.cache.ip
    end
    return util.client_ip()
end

local function is_private_client(extractor)
    local ctx = ngx.ctx
    if ctx._geo_private_ip ~= nil then
        return ctx._geo_private_ip
    end
    local priv = util.is_private_ip(client_ip(extractor))
    ctx._geo_private_ip = priv
    return priv
end

function _M.read_vars(extractor)
    local ctx = ngx.ctx
    if ctx._geo_vars then
        return ctx._geo_vars
    end
    if is_private_client(extractor) then
        ctx._geo_vars = EMPTY_VARS
        return EMPTY_VARS
    end
    local out = {}
    for _, f in ipairs(FIELDS) do
        local v = ngx.var[f.var]
        if not present(v) and f.fallback then
            v = ngx.var[f.fallback]
        end
        if f.tonumber and v ~= nil and v ~= "" then
            v = tonumber(v)
        end
        out[f.name] = v
    end
    ctx._geo_vars = out
    return out
end

-- Used by extractor during rule matching (only when geo.* is referenced).
function _M.field(extractor, name)
    if is_private_client(extractor) then
        if extractor and extractor.cache then
            extractor.cache[cache_key(name)] = false
        end
        return nil
    end
    if extractor and extractor.cache then
        local key = cache_key(name)
        if extractor.cache[key] ~= nil then
            local cached = extractor.cache[key]
            if cached == false then
                return nil
            end
            return cached
        end
    end
    local vars = _M.read_vars(extractor)
    local v = vars[name]
    if extractor and extractor.cache then
        extractor.cache[cache_key(name)] = v ~= nil and v or false
    end
    return v
end

function _M.trace_value(trace, name)
    local field = TRACE_BY_NAME[name]
    if not field then
        return nil
    end
    return trace_pick(trace, field)
end

-- Fill log entry geo_* columns: trace first, ngx.var only for gaps.
function _M.fill_entry(entry, trace, extractor)
    if type(entry) ~= "table" then
        return
    end
    if is_private_client(extractor) then
        return
    end
    local need_vars = false
    for _, f in ipairs(FIELDS) do
        if not present(entry[f.entry]) then
            local v = _M.trace_value(trace, f.name)
            if present(v) then
                entry[f.entry] = v
            else
                need_vars = true
            end
        end
    end
    if not need_vars then
        return
    end
    local vars = _M.read_vars(extractor)
    for _, f in ipairs(FIELDS) do
        if not present(entry[f.entry]) then
            local v = vars[f.name]
            if present(v) then
                entry[f.entry] = v
            end
        end
    end
end

return _M
