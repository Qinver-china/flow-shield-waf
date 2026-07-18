-- Access-phase orchestrator. Runs the full WAF decision pipeline:
--   challenge-verify endpoint -> whitelist -> blacklist -> exceptions
--   -> rate limits -> custom rules.
local sync = require "waf.sync"
local extractor = require "waf.extractor"
local matcher = require "waf.matcher"
local block = require "waf.actions.block"
local challenge = require "waf.actions.challenge"
local log_trace = require "waf.log_trace"
local log_emit = require "waf.log_emit"
local traffic_counter = require "waf.traffic_counter"
local debug_headers = require "waf.debug_headers"

local _M = {}

local function make_request_id()
    if ngx.var.request_id and ngx.var.request_id ~= "" then
        return ngx.var.request_id
    end
    return ngx.md5(table.concat({
        tostring(ngx.now()),
        ngx.var.remote_addr or "",
        ngx.var.request_uri or "",
        tostring(math.random(1, 1000000000)),
    }, "|"))
end

local function make_ctx(site_id, domain, settings)
    settings = settings or {}
    return {
        request_id = make_request_id(),
        site_id = site_id,
        domain = domain,
        js_challenge_ttl = settings.js_challenge_ttl or settings.challenge_ttl or 1800,
        captcha_ttl = settings.captcha_ttl or settings.challenge_ttl or 1800,
    }
end

local function rule_meta(source, id, name, keys)
    return {
        type = source == "rule" and "protection" or "access-control",
        source = source,
        id = id,
        name = name,
        keys = keys,
    }
end

local function rule_cleared(meta, ext)
    return challenge.is_cleared({
        source = meta.source,
        rule_id = meta.id,
        keys = meta.keys,
    }, ext)
end

-- Apply a protection mode. Returns "continue" to keep evaluating, or exits the
-- request for terminal actions (block / captcha / js_challenge / slide_captcha).
local function apply_mode(cfg, site, ctx, mode, meta, ext, trace)
    mode = mode or "block"
    debug_headers.apply(cfg, ctx, mode, meta)
    if mode == "observe" then
        log_emit.emit(cfg, ctx, meta, mode, false, trace, ext)
        return "continue"
    elseif mode == "block" then
        log_emit.emit(cfg, ctx, meta, mode, true, trace, ext)
        return block.run(cfg, site, ctx, meta)
    elseif mode == "captcha" then
        if rule_cleared(meta, ext) then return "continue" end
        log_emit.emit(cfg, ctx, meta, mode, true, trace, ext)
        return challenge.captcha(cfg, site, ctx, meta)
    elseif mode == "js_challenge" then
        if rule_cleared(meta, ext) then return "continue" end
        log_emit.emit(cfg, ctx, meta, mode, true, trace, ext)
        local res = challenge.js_challenge(ctx, meta)
        if res == "continue" then return "continue" end
        return res
    elseif mode == "slide_captcha" then
        if rule_cleared(meta, ext) then return "continue" end
        log_emit.emit(cfg, ctx, meta, mode, true, trace, ext)
        return challenge.slide_captcha(cfg, site, ctx, meta)
    else
        log_emit.emit(cfg, ctx, meta, "block", true, trace, ext)
        return block.run(cfg, site, ctx, meta)
    end
end

function _M.run()
    if sync.needs_load() then
        sync.load(true)
    end
    local cfg = sync.get()
    local ext = extractor.new()
    local domain = ngx.var.host
    local site = sync.site_by_domain(domain)
    local site_id = site and site.id or tonumber(ngx.var.waf_site_id)
    ext.cache.site_id = site_id
    local ctx = make_ctx(site_id, domain, cfg.settings)

    if ngx.var.uri == "/.waf/challenge-submit"
        or ngx.var.uri == "/.waf/captcha-verify" then
        if ngx.req.get_method() == "POST" then
            return challenge.handle_captcha_verify(ctx)
        end
        return ngx.redirect("/", ngx.HTTP_SEE_OTHER)
    end
    if ngx.var.uri == "/.waf/js-verify"
        and (ngx.req.get_method() == "GET" or ngx.req.get_method() == "POST") then
        return challenge.handle_js_verify(ctx)
    end
    if ngx.var.uri == "/.waf/slide-captcha/issue" and ngx.req.get_method() == "GET" then
        return challenge.handle_slide_issue()
    end
    if ngx.var.uri == "/.waf/slide-captcha/verify" and ngx.req.get_method() == "POST" then
        return challenge.handle_slide_verify(ctx)
    end

    traffic_counter.inc(site_id)

    local function applies(item)
        local site_ids = item.site_ids
        if not site_ids or type(site_ids) ~= "table" or #site_ids == 0 then
            return true
        end
        if site_id == nil then return false end
        for _, sid in ipairs(site_ids) do
            if tonumber(sid) == tonumber(site_id) then return true end
        end
        return false
    end

    for _, w in ipairs(cfg.whitelist) do
        if w.enabled ~= false and applies(w) and matcher.match(w.conditions, ext) then
            return
        end
    end

    for _, b in ipairs(cfg.blacklist) do
        if b.enabled ~= false and applies(b) then
            local matched, trace = log_trace.match(matcher, b.conditions, ext)
            if matched then
                return apply_mode(cfg, site, ctx, "block",
                    rule_meta("blacklist", b.id, b.name, nil), ext, trace)
            end
        end
    end

    local skip_all, skip_rules, skip_rate = false, false, false
    for _, e in ipairs(cfg.exceptions) do
        if e.enabled ~= false and applies(e) and matcher.match(e.conditions, ext) then
            local scope = e.scope or "all"
            if scope == "all" then
                skip_all = true
            elseif scope == "rules" then
                skip_rules = true
            elseif scope == "ratelimit" then
                skip_rate = true
            end
        end
    end
    if skip_all then return end

    if not skip_rate then
        for _, rl in ipairs(cfg.ratelimits) do
            if rl.enabled ~= false and applies(rl) then
                local meta = rule_meta("ratelimit", rl.id, rl.name, rl.keys)
                local hit, trace = log_trace.ratelimit_hit(rl, ext, function()
                    local rl_mode = rl.mode or "block"
                    return (rl_mode == "captcha" or rl_mode == "js_challenge" or rl_mode == "slide_captcha")
                        and rule_cleared(meta, ext)
                end, cfg)
                if hit then
                    local res = apply_mode(cfg, site, ctx, rl.mode or "block", meta, ext, trace)
                    if res ~= "continue" then return end
                end
            end
        end
    end

    if not skip_rules then
        for _, r in ipairs(cfg.rules) do
            if r.enabled ~= false and applies(r) then
                local matched, trace = log_trace.match(matcher, r.conditions, ext)
                if matched then
                    local res = apply_mode(cfg, site, ctx, r.mode, rule_meta("rule", r.id, r.name, nil), ext, trace)
                    if res ~= "continue" then return end
                end
            end
        end
    end
end

return _M
