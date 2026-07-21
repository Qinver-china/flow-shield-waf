-- init_worker: start config sync + reload watch + traffic counter timer
local sync = require "waf.sync"
local reloader = require "waf.reloader"
local catalog = require "waf.catalog"
local traffic_counter = require "waf.traffic_counter"

local _M = {}

local POLL_INTERVAL = 3
local TRAFFIC_INTERVAL = 1

local function poll(premature)
    if premature then return end
    local ok, err = pcall(sync.load)
    if not ok then
        ngx.log(ngx.ERR, "waf init: sync error: ", err)
    end
    local ok2, err2 = pcall(reloader.check)
    if not ok2 then
        ngx.log(ngx.ERR, "waf init: reload check error: ", err2)
    end
end

local function traffic_tick(premature)
    if premature then return end
    local ok, err = pcall(function()
        traffic_counter.tick(sync.get())
    end)
    if not ok then
        ngx.log(ngx.ERR, "waf init: traffic tick error: ", err)
    end
end

local function traffic_hydrate(premature)
    if premature then return end
    local ok, err = pcall(traffic_counter.hydrate_from_redis)
    if not ok then
        ngx.log(ngx.ERR, "waf init: traffic hydrate error: ", err)
    end
end

function _M.start()
    pcall(catalog.load)

    local ok, err = ngx.timer.at(0, poll)
    if not ok then
        ngx.log(ngx.ERR, "waf init: failed to create initial timer: ", err)
    end
    local ok2, err2 = ngx.timer.every(POLL_INTERVAL, poll)
    if not ok2 then
        ngx.log(ngx.ERR, "waf init: failed to create poll timer: ", err2)
    end
    local okh, errh = ngx.timer.at(2, traffic_hydrate)
    if not okh then
        ngx.log(ngx.ERR, "waf init: failed to create traffic hydrate timer: ", errh)
    end
    local ok3, err3 = ngx.timer.every(TRAFFIC_INTERVAL, traffic_tick)
    if not ok3 then
        ngx.log(ngx.ERR, "waf init: failed to create traffic timer: ", err3)
    end
end

return _M
