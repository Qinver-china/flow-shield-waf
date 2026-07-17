-- Evaluate a condition tree (shared JSON structure) against a request.
-- Node forms:
--   leaf:  { field=, arg=, op=, value= }
--   group: { logic="and"|"or", conditions={ ... } }
local operators = require "waf.operators"
local catalog = require "waf.catalog"
local traffic_compare = require "waf.traffic_compare"
local ip_groups = require "waf.ip_groups"

local _M = {}

local function is_group(node)
    return node.conditions ~= nil
end

local function match_leaf(node, ext)
    if catalog.loaded() and not catalog.is_valid(node.field) then
        ngx.log(ngx.WARN, "waf matcher: unknown field (not in catalog): ",
            tostring(node.field))
    end
    if node.field == "traffic.global" and node.op == "compare" then
        return traffic_compare.match(node.value)
    end
    if node.op == "in_ip_group" or node.op == "not_in_ip_group" then
        local ip = ext:get(node.field, node.arg)
        local matched = ip_groups.ip_in_groups(ip, node.value)
        if node.op == "not_in_ip_group" then
            return not matched
        end
        return matched
    end
    local value = ext:get(node.field, node.arg)
    return operators.apply(node.op, value, node.value)
end

local function match_node(node, ext)
    if is_group(node) then
        local logic = (node.logic or "and"):lower()
        local conds = node.conditions or {}
        if #conds == 0 then return true end
        if logic == "or" then
            for _, c in ipairs(conds) do
                if match_node(c, ext) then return true end
            end
            return false
        else -- and
            for _, c in ipairs(conds) do
                if not match_node(c, ext) then return false end
            end
            return true
        end
    else
        return match_leaf(node, ext)
    end
end

-- Public: match a top-level condition object against the extractor.
-- An empty / nil condition matches everything (used by exceptions/lists that
-- want to target "all").
function _M.match(condition, ext)
    if condition == nil then return true end
    if type(condition) ~= "table" then return false end
    local ok, res = pcall(match_node, condition, ext)
    if not ok then
        ngx.log(ngx.WARN, "waf matcher error: ", res)
        return false
    end
    return res
end

return _M
