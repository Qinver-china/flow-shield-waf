-- Build log payload: always capture zero-cost request snapshot, plus traced
-- fields that required expensive or lazy evaluation during rule matching.
local cjson = require "cjson.safe"
local util = require "waf.util"

local _M = {}

local MAX_VALUE = 4096

-- Fields already covered by the baseline snapshot; omit from evaluated list.
local BASELINE_COVERED = {
    ["ip.src"] = true,
    ["ip.src.is_private"] = true,
    ["net.src_port"] = true,
    ["net.dst_port"] = true,
    ["net.scheme"] = true,
    ["http.version"] = true,
    ["http.method"] = true,
    ["http.host"] = true,
    ["http.url"] = true,
    ["http.request_uri"] = true,
    ["http.uri.path"] = true,
    ["http.uri.ext"] = true,
    ["http.uri.depth"] = true,
    ["http.uri.query"] = true,
    ["http.query"] = true,
    ["http.query.count"] = true,
    ["http.header"] = true,
    ["http.header.count"] = true,
    ["http.ua"] = true,
    ["http.referer"] = true,
    ["http.content_type"] = true,
    ["http.content_length"] = true,
    ["http.accept"] = true,
    ["http.accept_language"] = true,
    ["http.accept_encoding"] = true,
    ["http.origin"] = true,
    ["http.xff"] = true,
    ["http.range"] = true,
    ["http.has_auth"] = true,
    ["http.cookie"] = true,
    ["http.cookie_raw"] = true,
    ["http.cookie.count"] = true,
}

local function truncate(s)
    if type(s) ~= "string" then
        return s
    end
    if #s <= MAX_VALUE then
        return s
    end
    return s:sub(1, MAX_VALUE) .. "…"
end

local function serialize_scalar(value)
    if value == nil then
        return nil
    end
    if type(value) == "boolean" or type(value) == "number" then
        return value
    end
    if type(value) == "table" then
        return truncate(cjson.encode(value))
    end
    return truncate(tostring(value))
end

local function serialize_map(map)
    local out = {}
    if type(map) ~= "table" then
        return out
    end
    for k, v in pairs(map) do
        if type(v) == "table" then
            local parts = {}
            for i, item in ipairs(v) do
                parts[i] = tostring(item)
            end
            out[tostring(k)] = truncate(table.concat(parts, ", "))
        else
            out[tostring(k)] = serialize_scalar(v)
        end
    end
    return out
end

local function normalize_headers(headers)
    local out = {}
    if type(headers) ~= "table" then
        return out
    end
    for k, v in pairs(headers) do
        local key = tostring(k)
        if type(v) == "table" then
            local parts = {}
            for i, item in ipairs(v) do
                parts[i] = tostring(item)
            end
            out[key] = truncate(table.concat(parts, ", "))
        else
            out[key] = truncate(tostring(v))
        end
    end
    return out
end

local function parse_cookies(raw)
    local map = {}
    if not raw or raw == "" then
        return map
    end
    for k, v in raw:gmatch("([^%s;=]+)=([^;]*)") do
        map[k] = v
    end
    return map
end

local function header_lookup(headers, name)
    if type(headers) ~= "table" then
        return nil
    end
    local lower = name:lower()
    for k, v in pairs(headers) do
        if tostring(k):lower() == lower then
            if type(v) == "table" then
                return v[1]
            end
            return v
        end
    end
    return nil
end

local function trace_pick(trace, field, arg)
    if type(trace) ~= "table" then
        return nil
    end
    local key = field
    if arg and arg ~= "" then
        key = field .. "|" .. tostring(arg)
    end
    local item = trace[key]
    return item and item.value
end

local function normalize_ip(ip)
    if not ip or ip == "" then
        return nil
    end
    local mapped = ip:match("^::ffff:(%d+%.%d+%.%d+%.%d+)$")
    if mapped then
        return mapped
    end
    return ip
end

-- Client IP is mandatory on every log row; resolve from all zero-cost sources.
function _M.resolve_client_ip(ext, trace)
    local ip = normalize_ip(util.client_ip())
    if ip and ip ~= "" then
        return ip
    end
    ip = normalize_ip(ngx.var.remote_addr)
    if ip and ip ~= "" then
        return ip
    end
    if ext and ext.cache and ext.cache.ip and ext.cache.ip ~= "" then
        return ext.cache.ip
    end
    ip = trace_pick(trace, "ip.src")
    if ip and ip ~= "" then
        return tostring(ip)
    end
    return ngx.var.remote_addr or ""
end

-- Zero-cost request data available as soon as the request arrives.
function _M.capture_baseline(ext, trace)
    local headers
    local cookies
    local query

    if ext then
        headers = ext:_headers()
        cookies = ext:_cookies()
        query = ext:_uri_args()
    else
        headers = ngx.req.get_headers() or {}
        cookies = parse_cookies(ngx.var.http_cookie)
        query = ngx.req.get_uri_args(0) or {}
    end

    local scheme = ngx.var.scheme or "http"
    local host = ngx.var.host or ""
    local request_uri = ngx.var.request_uri or ""
    local http_ver = ngx.req.http_version and ngx.req.http_version()
    if http_ver then
        http_ver = "HTTP/" .. tostring(http_ver)
    else
        http_ver = ngx.var.server_protocol
    end

    local client_ip = _M.resolve_client_ip(ext, trace)

    return {
        client_ip = client_ip,
        client = {
            ip = client_ip,
            port = tonumber(ngx.var.remote_port),
        },
        request = {
            method = ngx.req.get_method(),
            uri = request_uri,
            host = host,
            domain = host,
            scheme = scheme,
            url = scheme .. "://" .. host .. request_uri,
            http_version = http_ver,
            client_ip = client_ip,
        },
        headers = normalize_headers(headers),
        cookies = serialize_map(cookies),
        query = serialize_map(query),
        cookie_raw = truncate(ngx.var.http_cookie or ""),
    }
end

function _M.evaluated_fields(trace)
    local list = {}
    if type(trace) ~= "table" then
        return list
    end
    for _, item in pairs(trace) do
        if not BASELINE_COVERED[item.field] then
            list[#list + 1] = {
                field = item.field,
                arg = item.arg,
                value = serialize_scalar(item.value),
            }
        end
    end
    table.sort(list, function(a, b)
        local ka = (a.field or "") .. "|" .. tostring(a.arg or "")
        local kb = (b.field or "") .. "|" .. tostring(b.arg or "")
        return ka < kb
    end)
    return list
end

function _M.summary_columns(trace, ext, captured)
    local baseline = captured or _M.capture_baseline(ext, trace)
    local ua = header_lookup(baseline.headers, "user-agent")
        or ngx.var.http_user_agent
        or trace_pick(trace, "http.ua")
    return {
        client_ip = baseline.client_ip,
        geo_country = trace_pick(trace, "geo.country"),
        ua = ua and truncate(tostring(ua)) or nil,
    }
end

function _M.build_baseline(trace, meta, ext, captured)
    meta = meta or {}
    local baseline = captured or _M.capture_baseline(ext, trace)
    return {
        client_ip = baseline.client_ip,
        client = baseline.client,
        request = baseline.request,
        headers = baseline.headers,
        cookies = baseline.cookies,
        cookie_raw = baseline.cookie_raw,
        query = baseline.query,
        rule = {
            source = meta.source,
            id = meta.id,
            name = meta.name,
            keys = meta.keys,
        },
    }
end

function _M.build(trace, meta, ext)
    local out = _M.build_baseline(trace, meta, ext)
    out.evaluated = _M.evaluated_fields(trace)
    return out
end

return _M
