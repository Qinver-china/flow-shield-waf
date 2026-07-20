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

local function match_crawler_raw(cfg, ua)
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

function _M.match_crawler(cfg, ua, ext)
    if ext and ext.cache.crawler_match_resolved then
        return ext.cache.crawler_match_name
    end
    local name = match_crawler_raw(cfg, ua)
    if ext then
        ext.cache.crawler_match_resolved = true
        ext.cache.crawler_match_name = name
    end
    return name
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

local function item_categories(item)
    local cats = item.categories
    local out = {}
    local seen = {}
    if type(cats) == "table" then
        for _, c in ipairs(cats) do
            if type(c) == "string" and c ~= "" and not seen[c] then
                seen[c] = true
                out[#out + 1] = c
            end
        end
    end
    if #out > 0 then
        return out
    end
    if type(item.category) == "string" and item.category ~= "" then
        return { item.category }
    end
    return { OTHER_CATEGORY }
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
        if applies(item, site_id) then
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
                    local categories = item_categories(item)
                    local match = {
                        id = item.id,
                        name = item.name,
                        categories = categories,
                        category = categories[1],
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

local function ensure_ua_family(cfg, ext, site_id)
    if ext.cache.ua_family ~= nil then
        return ext.cache.ua_family
    end
    local ua_parse = require "waf.ua_parse"
    local ua = ext:get("http.ua")
    return ua_parse.family(ua, cfg, ext, site_id)
end

local function clear_bot_dimensions(ext)
    ext.cache.bot_name = nil
    ext.cache.bot_category = nil
    ext.cache.bot_categories = nil
end

function _M.resolve_dimensions(cfg, ext, site_id)
    if ext.cache.bot_dimensions_resolved then
        return ext.cache.bot_name, ext.cache.bot_category
    end
    ext.cache.bot_dimensions_resolved = true
    ext.cache.bot_name_resolved = true

    local fam = ensure_ua_family(cfg, ext, site_id)
    if fam ~= "bot" then
        clear_bot_dimensions(ext)
        return nil, nil
    end

    local match = _M.identify(cfg, ext, site_id)
    if match then
        ext.cache.bot_name = match.name
        ext.cache.bot_categories = match.categories
        ext.cache.bot_category = match.category
        return match.name, match.category
    end

    local ua = ext:get("http.ua")
    local crawler_name = _M.match_crawler(cfg, ua, ext)
    if crawler_name then
        ext.cache.bot_name = crawler_name
        ext.cache.bot_categories = { OTHER_CATEGORY }
        ext.cache.bot_category = OTHER_CATEGORY
        return crawler_name, OTHER_CATEGORY
    end

    if _M.is_bot_ua(ua) then
        ext.cache.bot_name = nil
        ext.cache.bot_categories = { OTHER_CATEGORY }
        ext.cache.bot_category = OTHER_CATEGORY
        return nil, OTHER_CATEGORY
    end

    clear_bot_dimensions(ext)
    return nil, nil
end

function _M.resolve_name(cfg, ext, site_id)
    local name, _ = _M.resolve_dimensions(cfg, ext, site_id)
    return name
end

function _M.resolve_category(cfg, ext, site_id)
    local _, category = _M.resolve_dimensions(cfg, ext, site_id)
    return category
end

function _M.resolve_categories(cfg, ext, site_id)
    _M.resolve_dimensions(cfg, ext, site_id)
    if ext.cache.bot_categories then
        return ext.cache.bot_categories
    end
    if ext.cache.bot_category then
        return { ext.cache.bot_category }
    end
    return nil
end

return _M
