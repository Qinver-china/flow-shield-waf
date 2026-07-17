-- Operator implementations. apply(op, value, target) -> boolean
-- `value` is extracted from the request, `target` comes from the rule.
local util = require "waf.util"

local _M = {}

local function tostr(v)
    if v == nil then return nil end
    if type(v) == "boolean" then return v and "true" or "false" end
    return tostring(v)
end

local function tonum(v)
    if type(v) == "number" then return v end
    return tonumber(v)
end

-- tonumber() in Lua parses numeric prefixes ("192.168.65.1" -> 192), which breaks
-- IP equality. Only treat values as numbers when the whole string is numeric.
local function is_numeric_operand(v)
    if type(v) == "number" then return true end
    if type(v) ~= "string" then return false end
    if v:match("^%-?%d+$") then return true end
    if v:match("^%-?%d+%.%d+$") then return true end
    return false
end

local function numeric_eq(v, t)
    if is_numeric_operand(v) and is_numeric_operand(t) then
        return tonum(v) == tonum(t)
    end
    return tostr(v) == tostr(t)
end

local function numeric_neq(v, t)
    if is_numeric_operand(v) and is_numeric_operand(t) then
        return tonum(v) ~= tonum(t)
    end
    return tostr(v) ~= tostr(t)
end

local function as_list(target)
    if type(target) == "table" then return target end
    return { target }
end

local function in_list(value, target)
    local sv = tostr(value)
    for _, item in ipairs(as_list(target)) do
        if tostr(item) == sv then return true end
    end
    return false
end

local OPS = {}

-- string
OPS.equals = function(v, t) return tostr(v) == tostr(t) end
OPS.not_equals = function(v, t) return tostr(v) ~= tostr(t) end
OPS.contains = function(v, t)
    local sv = tostr(v); local st = tostr(t)
    return sv ~= nil and st ~= nil and sv:find(st, 1, true) ~= nil
end
OPS.not_contains = function(v, t) return not OPS.contains(v, t) end
OPS.starts_with = function(v, t)
    local sv = tostr(v); local st = tostr(t)
    return sv ~= nil and st ~= nil and sv:sub(1, #st) == st
end
OPS.ends_with = function(v, t)
    local sv = tostr(v); local st = tostr(t)
    return sv ~= nil and st ~= nil and (#st == 0 or sv:sub(-#st) == st)
end
OPS.regex = function(v, t)
    local sv = tostr(v)
    if sv == nil then return false end
    local m = ngx.re.find(sv, tostr(t), "joi")
    return m ~= nil
end
OPS.in_list = in_list
OPS.not_in = function(v, t) return not in_list(v, t) end
OPS.is_empty = function(v) return v == nil or tostr(v) == "" end
OPS.exists = function(v) return v ~= nil end
OPS.len_gt = function(v, t)
    local sv = tostr(v); return sv ~= nil and #sv > (tonum(t) or 0)
end
OPS.len_lt = function(v, t)
    local sv = tostr(v); return sv ~= nil and #sv < (tonum(t) or 0)
end

-- number (and non-numeric operands fall back to string equality)
OPS.eq = numeric_eq
OPS.neq = numeric_neq
OPS.gt = function(v, t) local nv, nt = tonum(v), tonum(t); return nv and nt and nv > nt end
OPS.gte = function(v, t) local nv, nt = tonum(v), tonum(t); return nv and nt and nv >= nt end
OPS.lt = function(v, t) local nv, nt = tonum(v), tonum(t); return nv and nt and nv < nt end
OPS.lte = function(v, t) local nv, nt = tonum(v), tonum(t); return nv and nt and nv <= nt end
OPS.between = function(v, t)
    local nv = tonum(v)
    local lo = tonum(t[1]); local hi = tonum(t[2])
    return nv and lo and hi and nv >= lo and nv <= hi
end

-- ip
OPS.in_cidr = function(v, t)
    if v == nil then return false end
    for _, cidr in ipairs(as_list(t)) do
        if util.ip_in_cidr(v, cidr) then return true end
    end
    return false
end
OPS.geo_in = in_list

-- map presence
OPS.key_exists = function(v) return v ~= nil end
OPS.key_absent = function(v) return v == nil end

function _M.apply(op, value, target)
    local fn = OPS[op]
    if not fn then
        ngx.log(ngx.WARN, "waf operators: unknown op ", tostring(op))
        return false
    end
    local ok, res = pcall(fn, value, target)
    if not ok then
        ngx.log(ngx.WARN, "waf operators: op ", op, " error: ", res)
        return false
    end
    return res and true or false
end

return _M
