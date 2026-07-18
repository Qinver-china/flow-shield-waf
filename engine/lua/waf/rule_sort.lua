-- Rule ordering helpers (mirrors matcher catch-all semantics).
local _M = {}

local function is_group(node)
    return type(node) == "table" and node.conditions ~= nil
end

-- Same truth conditions as matcher.match for "matches every request".
function _M.is_catch_all_condition(condition)
    if condition == nil then
        return true
    end
    if type(condition) ~= "table" then
        return false
    end
    if is_group(condition) then
        return #(condition.conditions or {}) == 0
    end
    return false
end

function _M.is_catch_all_observe_rule(rule)
    if type(rule) ~= "table" or rule.enabled == false then
        return false
    end
    if (rule.mode or "block") ~= "observe" then
        return false
    end
    return _M.is_catch_all_condition(rule.conditions)
end

function _M.sort_rules(items)
    table.sort(items or {}, function(a, b)
        local a_tail = _M.is_catch_all_observe_rule(a) and 1 or 0
        local b_tail = _M.is_catch_all_observe_rule(b) and 1 or 0
        if a_tail ~= b_tail then
            return a_tail < b_tail
        end
        return (a.priority or 100) < (b.priority or 100)
    end)
    return items
end

return _M
