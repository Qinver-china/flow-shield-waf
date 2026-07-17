-- Watches Redis key `waf:nginx:reload`; when it changes (backend added/changed
-- a site), one worker runs `openresty -s reload` so new server blocks in
-- conf.d take effect. A shared-dict lock ensures only one worker reloads.
local rc = require "waf.redis_client"

local _M = {}

local RELOAD_KEY = "waf:nginx:reload"
local locks = ngx.shared.waf_locks

function _M.check()
    local red, err = rc.connect()
    if not red then
        return
    end
    local ver = red:get(RELOAD_KEY)
    rc.release(red)
    if ver == nil or ver == ngx.null then
        return
    end
    ver = tonumber(ver) or 0

    local last = locks:get("reload_ver") or 0
    if ver <= last then
        return
    end

    -- try to claim the reload (only one worker wins)
    local ok = locks:add("reload_lock", 1, 10)
    if not ok then
        -- another worker is handling it; record the version to avoid re-check
        locks:set("reload_ver", ver)
        return
    end

    locks:set("reload_ver", ver)
    ngx.log(ngx.NOTICE, "waf reloader: reloading nginx (version ", ver, ")")
    -- Backend normally reloads as root; this is a fallback for standalone engine setups.
    os.execute(
        "/usr/local/openresty/bin/openresty -s reload "
            .. "-c /usr/local/openresty/nginx/conf/nginx.conf "
            .. "2>/dev/null"
    )
    locks:delete("reload_lock")
end

return _M
