-- Resolve IP group references from synced config.
local sync = require "waf.sync"
local util = require "waf.util"

local _M = {}

local function group_map()
    local cfg = sync.get()
    return (cfg and cfg.ip_groups) or {}
end

local function entries_for_groups(group_ids)
    local groups = group_map()
    local entries = {}
    if type(group_ids) ~= "table" then
        group_ids = { group_ids }
    end
    for _, gid in ipairs(group_ids) do
        local key = tostring(gid)
        local group = groups[key]
        if group and type(group.entries) == "table" then
            for _, entry in ipairs(group.entries) do
                entries[#entries + 1] = entry
            end
        end
    end
    return entries
end

function _M.ip_in_groups(ip, group_ids)
    if not ip or ip == "" then
        return false
    end
    for _, entry in ipairs(entries_for_groups(group_ids)) do
        if util.ip_in_cidr(ip, entry) then
            return true
        end
    end
    return false
end

return _M
