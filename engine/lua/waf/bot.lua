-- Bot identification helpers (library only; no interception).
local sync = require "waf.sync"

local _M = {}

local OTHER_CATEGORY = "other"

local function cfg_bots(cfg)
    cfg = cfg or sync.get()
    return (cfg and cfg.bots) or {}
end

local function cfg_crawler_detect(cfg)
    cfg = cfg or sync.get()
    return cfg and cfg.crawler_detect
end

function _M.match_crawler(cfg, ua)
    if not ua or ua == "" then
        return nil
    end
    local cd = cfg_crawler_detect(cfg)
    if not cd then
        return nil
    end

    local agent = ua
    local exclusions = cd.exclusions
    if exclusions and exclusions ~= "" then
        local ok, stripped = pcall(function()
            return ngx.re.gsub(agent, exclusions, "", "ioj")
        end)
        if ok and stripped then
            agent = stripped
        end
    end
    if agent == "" then
        return nil
    end

    local patterns = cd.patterns
    if not patterns or patterns == "" then
        return nil
    end
    local ok, match = pcall(function()
        return ngx.re.match(agent, patterns, "ioj")
    end)
    if not ok or not match then
        return nil
    end
    for i = 1, #match do
        local name = match[i]
        if name and name ~= "" then
            return name
        end
    end
    if match[0] and match[0] ~= "" then
        return match[0]
    end
    return nil
end

function _M.is_bot_ua(ua)
    if not ua or ua == "" then
        return false
    end
    local ua_l = string.lower(ua)
    return ua_l:find("bot", 1, true) ~= nil
        or ua_l:find("spider", 1, true) ~= nil
        or ua_l:find("crawl", 1, true) ~= nil
end

local function pattern_match(ua, pattern)
    if not ua or not pattern or pattern == "" then
        return false
    end
    local body, flags = pattern:match("^/(.*)/([a-z]*)$")
    if body then
        local ok, matched = pcall(function()
            return ngx.re.find(ua, body, flags or "jo")
        end)
        return ok and matched ~= nil
    end
    return string.find(string.lower(ua), string.lower(pattern), 1, true) ~= nil
end

local function applies(item, site_id)
    local site_ids = item.site_ids
    if not site_ids or type(site_ids) ~= "table" or #site_ids == 0 then
        return true
    end
    if site_id == nil then
        return false
    end
    for _, sid in ipairs(site_ids) do
        if tonumber(sid) == tonumber(site_id) then
            return true
        end
    end
    return false
end

function _M.verify_dns(_ip, _suffix)
    -- Reserved for reverse-DNS verification of claimed bots.
    return false
end

function _M.identify(cfg, ext, site_id)
    if ext.cache.bot_identified then
        return ext.cache.bot
    end
    ext.cache.bot_identified = true
    local ua = ext:get("http.ua")
    if not ua or ua == "" then
        ext.cache.bot = nil
        return nil
    end

    for _, item in ipairs(cfg_bots(cfg)) do
        if item.enabled ~= false and applies(item, site_id) then
            local patterns = item.ua_patterns or {}
            for _, pattern in ipairs(patterns) do
                if pattern_match(ua, pattern) then
                    local verified = false
                    if item.verify_dns_suffix and item.verify_dns_suffix ~= "" then
                        local ip = ext.cache.ip
                        if not ip then
                            local util = require "waf.util"
                            ip = util.client_ip()
                            ext.cache.ip = ip
                        end
                        verified = _M.verify_dns(ip, item.verify_dns_suffix)
                    end
                    local match = {
                        id = item.id,
                        name = item.name,
                        category = item.category,
                        verified = verified,
                    }
                    ext.cache.bot = match
                    return match
                end
            end
        end
    end

    ext.cache.bot = nil
    return nil
end

function _M.resolve_name(cfg, ext, site_id)
    if ext.cache.bot_name_resolved then
        return ext.cache.bot_name
    end
    ext.cache.bot_name_resolved = true

    local match = _M.identify(cfg, ext, site_id)
    if match and match.name then
        ext.cache.bot_name = match.name
        return match.name
    end

    local ua = ext:get("http.ua")
    local crawler_name = _M.match_crawler(cfg, ua)
    ext.cache.bot_name = crawler_name
    return crawler_name
end

function _M.resolve_category(cfg, ext, site_id)
    local match = _M.identify(cfg, ext, site_id)
    if match and match.category then
        return match.category
    end
    local ua = ext:get("http.ua")
    if _M.match_crawler(cfg, ua) or _M.is_bot_ua(ua) then
        return OTHER_CATEGORY
    end
    return nil
end

return _M
