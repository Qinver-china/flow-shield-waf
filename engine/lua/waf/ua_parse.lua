-- Lightweight UA family / OS parsing for rule matching (aligned with log enrich).
local bot = require "waf.bot"
local sync = require "waf.sync"

local _M = {}

local OS_PATTERNS = {
    { "Android", "Android" },
    { "iPhone", "iOS" },
    { "iPad", "iOS" },
    { "Windows", "Windows" },
    { "Mac OS X", "macOS" },
    { "Mac OS", "macOS" },
    { "CrOS", "Chrome OS" },
    { "Linux", "Linux" },
}

function _M.family(ua, cfg, ext, site_id)
    if not ua or ua == "" then
        return nil
    end
    if ext and ext.cache.ua_family ~= nil then
        return ext.cache.ua_family
    end
    cfg = cfg or sync.get()
    local fam
    if bot.identify(cfg, ext, site_id) then
        fam = "bot"
    elseif bot.match_crawler(cfg, ua, ext) then
        fam = "bot"
    elseif bot.is_bot_ua(ua) then
        fam = "bot"
    else
        fam = "browser"
    end
    if ext then
        ext.cache.ua_family = fam
    end
    return fam
end

function _M.os(ua)
    if not ua or ua == "" then
        return nil
    end
    for _, pair in ipairs(OS_PATTERNS) do
        if ua:find(pair[1], 1, true) then
            return pair[2]
        end
    end
    return nil
end

return _M
