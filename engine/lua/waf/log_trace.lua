-- Traced rule evaluation helpers.
--
-- Flow:
--   1. access.lua calls log_trace.match / log_trace.ratelimit_hit before logging.
--   2. extractor:get() records each field read while trace is active (value captured once).
--   3. On hit, log_snapshot.build(trace) serializes only those fields — no re-fetch.
--
-- Clearance bypass (rule_cleared) runs outside the trace so fingerprint dims are not logged.
local matcher = require "waf.matcher"
local ratelimit = require "waf.ratelimit"

local _M = {}

function _M.merge(...)
    local out = {}
    for i = 1, select("#", ...) do
        local trace = select(i, ...)
        if type(trace) == "table" then
            for k, v in pairs(trace) do
                out[k] = v
            end
        end
    end
    return out
end

-- Match conditions and return { matched, trace }.
function _M.match(matcher_mod, condition, ext)
    if condition == nil then
        return true, {}
    end
    ext:trace_begin()
    local matched = matcher_mod.match(condition, ext)
    local trace = ext:trace_end() or {}
    return matched, trace
end

-- Rate-limit hit path: precond match + counter keys (clearance check is outside trace).
function _M.ratelimit_hit(rl, ext, cleared_fn, cfg)
    local t1 = {}
    local precond = true
    if rl.conditions ~= nil then
        precond, t1 = _M.match(matcher, rl.conditions, ext)
    end
    if not precond then
        return false, nil
    end
    if cleared_fn and cleared_fn() then
        return false, nil
    end
    ext:trace_begin()
    local exceeded = ratelimit.exceeded(rl, ext, cfg)
    local t2 = ext:trace_end() or {}
    if not exceeded then
        return false, nil
    end
    return true, _M.merge(t1, t2)
end

return _M
