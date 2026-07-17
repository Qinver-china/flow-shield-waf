-- Redis client with Unix socket / TCP, connection pool, reuse-aware auth, and retry.
local redis = require "resty.redis"

local _M = {}

local function env_int(name, default)
    local v = tonumber(os.getenv(name))
    if v == nil then
        return default
    end
    return v
end

local function cfg()
    local socket_path = os.getenv("REDIS_SOCKET_PATH")
    if socket_path and socket_path ~= "" then
        return {
            mode = "unix",
            socket_path = socket_path,
            password = os.getenv("REDIS_PASSWORD"),
        }
    end
    return {
        mode = "tcp",
        host = os.getenv("REDIS_HOST") or "127.0.0.1",
        port = tonumber(os.getenv("REDIS_PORT") or "6379"),
        password = os.getenv("REDIS_PASSWORD"),
    }
end

local function pool_keepalive_ms()
    return env_int("REDIS_KEEPALIVE_MS", 60000)
end

local function pool_size()
    return env_int("REDIS_POOL_SIZE", 256)
end

local function connect_timeout_ms()
    return env_int("REDIS_CONNECT_TIMEOUT_MS", 1000)
end

local function send_timeout_ms()
    return env_int("REDIS_SEND_TIMEOUT_MS", 2000)
end

local function read_timeout_ms()
    return env_int("REDIS_READ_TIMEOUT_MS", 2000)
end

local function connect_once(conf)
    local red = redis:new()
    red:set_timeouts(connect_timeout_ms(), send_timeout_ms(), read_timeout_ms())

    local ok, err
    if conf.mode == "unix" then
        ok, err = red:connect("unix:" .. conf.socket_path)
    else
        ok, err = red:connect(conf.host, conf.port)
    end
    if not ok then
        return nil, err or "connect failed"
    end

    local times, terr = red:get_reused_times()
    if times == nil then
        red:close()
        return nil, terr or "get_reused_times failed"
    end

    if times == 0 and conf.password and conf.password ~= "" then
        local aok, aerr = red:auth(conf.password)
        if not aok then
            red:close()
            return nil, aerr or "auth failed"
        end
    end

    return red, nil
end

-- Returns a connected redis client or nil, err
function _M.connect()
    local conf = cfg()
    local red, err = connect_once(conf)
    if red then
        return red
    end
    -- Brief backoff for transient bridge / socket errors under load.
    if ngx and ngx.sleep then
        ngx.sleep(0.002)
    end
    return connect_once(conf)
end

-- Put the connection back to the pool (force_close=true discards a bad socket).
function _M.release(red, force_close)
    if not red then
        return
    end
    if force_close then
        red:close()
        return
    end
    local ok = red:set_keepalive(pool_keepalive_ms(), pool_size())
    if not ok then
        red:close()
    end
end

function _M.close(red)
    _M.release(red, true)
end

return _M
