-- Decide whether a WAF hit should be logged and at what detail level.
local traffic = require "waf.traffic_counter"

local _M = {}

local function sample_bucket(request_id)
    local rid = request_id or tostring(ngx.now())
    local crc = ngx.crc32_long or ngx.crc32_short
    if crc then
        return crc(rid) % 10000
    end
    return tonumber(ngx.md5(rid):sub(1, 4), 16) % 10000
end

local function logging_cfg(cfg)
    local settings = (cfg and cfg.settings) or {}
    return settings.logging or {}
end

function _M.burst_active()
    return traffic.burst_active()
end

function _M.should_log(cfg, mode, request_id)
    local log = logging_cfg(cfg)
    local burst = traffic.burst_active()

    if burst then
        if mode == "observe" then
            local rate = tonumber(log.logging_auto_observe_sample_rate) or 1.0
            rate = math.max(0, math.min(1, rate))
            if rate <= 0 then
                return false, "burst_observe_zero"
            end
            if rate >= 1 then
                return true, "burst_observe_full"
            end
            local bucket = sample_bucket(request_id)
            if bucket < math.floor(rate * 10000) then
                return true, "burst_observe_sampled"
            end
            return false, "burst_observe_miss"
        end
        return true, "burst"
    end

    local control = log.logging_control_mode or "manual"
    if control == "auto_by_traffic" then
        if mode ~= "observe" then
            return true, "auto_idle_blocked"
        end
        return false, "auto_idle"
    end

    if log.logging_enabled == false then
        return false, "manual_off"
    end

    if mode == "observe" and log.logging_skip_observe then
        return false, "skip_observe"
    end

    if mode == "observe" then
        local rate
        if traffic.viewer_active() then
            rate = tonumber(log.observe_sample_rate_active) or 1.0
        else
            rate = tonumber(log.observe_sample_rate_idle) or 1.0
        end
        rate = math.max(0, math.min(1, rate))
        if rate <= 0 then
            return false, "observe_sample_zero"
        end
        if rate >= 1 then
            return true, "observe_full"
        end
        local bucket = sample_bucket(request_id)
        if bucket < math.floor(rate * 10000) then
            return true, "observe_sampled"
        end
        return false, "observe_miss"
    end

    return true, "always"
end

function _M.observe_sample_rate(cfg)
    local log = logging_cfg(cfg)
    if traffic.burst_active() then
        return tonumber(log.logging_auto_observe_sample_rate) or 1.0
    end
    if traffic.viewer_active() then
        return tonumber(log.observe_sample_rate_active) or 1.0
    end
    return tonumber(log.observe_sample_rate_idle) or 1.0
end

-- Heavy trace fields (body/json/geo lookups during rule match). Baseline snapshot
-- (headers, cookies, query) is always attached in log_emit regardless of this flag.
function _M.include_detail(cfg, mode)
    local log = logging_cfg(cfg)
    if mode == "observe" then
        return false
    end
    if log.logging_detail_on_block == false then
        return false
    end
    return mode == "block" or mode == "captcha" or mode == "js_challenge" or mode == "slide_captcha"
end

return _M
