-- Build compact log entries and schedule async push.
local log_snapshot = require "waf.log_snapshot"
local log_policy = require "waf.log_policy"
local events = require "waf.events"
local bot = require "waf.bot"
local ua_parse = require "waf.ua_parse"
local uri_parse = require "waf.uri_parse"
local geo_lookup = require "waf.geo_lookup"
local util = require "waf.util"

local _M = {}

local MAX_UA = 256

local function trace_pick(trace, field, arg)
    if type(trace) ~= "table" then return nil end
    local key = field
    if arg and arg ~= "" then key = field .. "|" .. tostring(arg) end
    local item = trace[key]
    return item and item.value
end

local function xff_first()
    local xff = ngx.var.http_x_forwarded_for
    if not xff or xff == "" then
        return nil
    end
    return xff:match("^%s*([^,%s]+)")
end

function _M.build_tier_a(ctx, meta, mode, blocked, trace, ext, captured)
    local summary = log_snapshot.summary_columns(trace, ext, captured)
    local path = uri_parse.path()
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
        method = ngx.req.get_method(),
        request_uri = uri_parse.request_uri(),
        uri_path = path,
        uri_ext = uri_parse.ext(path),
        uri_depth = uri_parse.depth(path),
        uri_query = uri_parse.query(),
        query_count = uri_parse.query_count(),
        scheme = ngx.var.scheme,
        http_version = ngx.var.server_protocol,
        ua = ua,
        rule_id = meta.id,
        rule_name = meta.name,
        action = mode,
        mode = mode,
        blocked = blocked,
        request_id = ctx.request_id,
        referer = uri_parse.referer(),
        referer_host = uri_parse.referer_host(),
        ip_is_private = trace_pick(trace, "ip.src.is_private")
            or util.is_private_ip(summary.client_ip),
        xff_first = xff_first(),
        tls_version = ngx.var.ssl_protocol,
        tls_cipher = ngx.var.ssl_cipher,
        tls_ja3 = ngx.var.http_ssl_ja3,
    }
end

local function merge_baseline(entry, baseline)
    entry.payload = baseline
end

local function enrich_bot_dimensions(entry, cfg, ext, site_id)
    local ua = entry.ua
    if not ua or ua == "" then
        return
    end
    entry.ua_family = ua_parse.family(ua, cfg, ext, site_id)
    entry.ua_os = ua_parse.os(ua)
    if entry.ua_family ~= "bot" then
        return
    end
    entry.bot_name, entry.bot_category = bot.resolve_dimensions(cfg, ext, site_id)
    entry.ua_browser = nil
end

function _M.emit(cfg, ctx, meta, mode, blocked, trace, ext)
    local ok_log, _reason = log_policy.should_log(cfg, mode, ctx.request_id)
    if not ok_log then
        return
    end

    local captured = log_snapshot.capture_baseline(ext, trace)
    local entry = _M.build_tier_a(ctx, meta, mode, blocked, trace, ext, captured)
    local baseline = log_snapshot.build_baseline(trace, meta, ext, captured)
    merge_baseline(entry, baseline)
    enrich_bot_dimensions(entry, cfg, ext, ctx.site_id)
    -- Lazy geo fill on log path only: reuse rule trace when present, else batch-read ngx.var.
    geo_lookup.fill_entry(entry, trace, ext)

    if log_policy.include_detail(cfg, mode) then
        entry.evaluated = log_snapshot.evaluated_fields(trace)
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
