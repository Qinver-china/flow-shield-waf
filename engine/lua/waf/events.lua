-- Push structured log entries to Redis Stream consumed by the backend worker.
local cjson = require "cjson.safe"
local rc = require "waf.redis_client"

local _M = {}

local STREAM_KEY = "waf:logs:stream"
local MAX_STREAM = 200000

function _M.push(entry)
    entry.ts = entry.ts or ngx.time()
    local payload = cjson.encode(entry)
    if not payload then return end

    local red, err = rc.connect()
    if not red then
        ngx.log(ngx.ERR, "waf events: redis connect failed: ", err)
        return
    end

    local ok, perr = red:xadd(STREAM_KEY, "MAXLEN", "~", MAX_STREAM, "*", "data", payload)
    if not ok then
        ngx.log(ngx.ERR, "waf events: push failed: ", perr)
    end
    rc.release(red)
end

return _M
