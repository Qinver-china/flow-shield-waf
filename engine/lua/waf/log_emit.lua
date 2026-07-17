-- Build compact log entries and schedule async push.
local log_snapshot = require "waf.log_snapshot"
local log_policy = require "waf.log_policy"
local events = require "waf.events"

local _M = {}

local MAX_UA = 256

local function trace_pick(trace, field, arg)
    if type(trace) ~= "table" then return nil end
    local key = field
    if arg and arg ~= "" then key = field .. "|" .. tostring(arg) end
    local item = trace[key]
    return item and item.value
end

local function referer_host()
    local ref = ngx.var.http_referer
    if not ref or ref == "" then return nil end
    local host = ref:match("^https?://([^/%?#:]+)")
    return host
end

local function uri_path()
    local uri = ngx.var.uri or "/"
    return uri
end

local function uri_ext(path)
    local ext = path:match("%.([%w%-]+)$")
    return ext
end

local function uri_depth(path)
    local depth = 0
    for _ in path:gmatch("/") do depth = depth + 1 end
    if depth > 0 then depth = depth - 1 end
    return depth
end

local function xff_first()
    local xff = ngx.var.http_x_forwarded_for
    if not xff or xff == "" then
        return nil
    end
    return xff:match("^%s*([^,%s]+)")
end

function _M.build_tier_a(ctx, meta, mode, blocked, trace, ext)
    local summary = log_snapshot.summary_columns(trace, ext)
    local path = uri_path()
    local ua = summary.ua or ngx.var.http_user_agent
    if ua and #ua > MAX_UA then
        ua = ua:sub(1, MAX_UA)
    end
    return {
        ts = ngx.time(),
        log_type = meta.type,
        source = meta.source,
        site_id = ctx.site_id,
        domain = ctx.domain,
        client_ip = summary.client_ip,
        geo_country = summary.geo_country or trace_pick(trace, "geo.country"),
        geo_region = trace_pick(trace, "geo.region"),
        geo_city = trace_pick(trace, "geo.city"),
        geo_ip_type = trace_pick(trace, "geo.ip_type"),
        method = ngx.req.get_method(),
        uri = ngx.var.request_uri,
        uri_path = path,
        uri_ext = uri_ext(path),
        uri_depth = uri_depth(path),
        scheme = ngx.var.scheme,
        http_version = ngx.var.server_protocol,
        ua = ua,
        rule_id = meta.id,
        rule_name = meta.name,
        action = mode,
        mode = mode,
        blocked = blocked,
        request_id = ctx.request_id,
        referer_host = referer_host(),
        ip_is_private = trace_pick(trace, "ip.src.is_private"),
        xff_first = xff_first(),
        tls_version = ngx.var.ssl_protocol,
        tls_cipher = ngx.var.ssl_cipher,
        tls_ja3 = ngx.var.http_ssl_ja3,
    }
end

local function merge_baseline(entry, baseline)
    entry.payload = baseline
    for k, v in pairs(baseline) do
        if entry[k] == nil then
            entry[k] = v
        end
    end
end

function _M.emit(cfg, ctx, meta, mode, blocked, trace, ext)
    local ok_log, _reason = log_policy.should_log(cfg, mode, ctx.request_id)
    if not ok_log then
        return
    end

    local entry = _M.build_tier_a(ctx, meta, mode, blocked, trace, ext)
    local baseline = log_snapshot.build_baseline(trace, meta, ext)
    merge_baseline(entry, baseline)

    if log_policy.include_detail(cfg, mode) then
        entry.evaluated = log_snapshot.evaluated_fields(trace)
        entry.payload.evaluated = entry.evaluated
    end

    local ok, err = ngx.timer.at(0, function(premature)
        if premature then return end
        events.push(entry)
    end)
    if not ok then
        ngx.log(ngx.ERR, "waf log_emit: timer failed: ", err)
    end
end

return _M
