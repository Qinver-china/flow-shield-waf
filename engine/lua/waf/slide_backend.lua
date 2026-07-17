-- HTTP client for slide captcha backend APIs (FastAPI on localhost).
-- Uses cosocket only — no lua-resty-http dependency.
local cjson = require "cjson.safe"

local _M = {}

local function backend_host()
    local url = os.getenv("WAF_BACKEND_URL") or "http://127.0.0.1:8000"
    local host, port = url:match("^https?://([^:/]+):?(%d*)")
    if not host then
        return "127.0.0.1", 8000
    end
    port = tonumber(port)
    if not port or port == 0 then
        port = 80
    end
    return host, port
end

local function request_once(method, path, body, extra_headers)
    local host, port = backend_host()
    local sock = ngx.socket.tcp()
    sock:settimeout(5000)
    local ok, err = sock:connect(host, port)
    if not ok then
        return nil, err or "connect failed"
    end

    local headers = {
        ["Host"] = host,
        ["Connection"] = "close",
        ["Accept"] = "application/json",
    }
    if extra_headers then
        for k, v in pairs(extra_headers) do
            headers[k] = v
        end
    end
    if body and body ~= "" then
        headers["Content-Type"] = headers["Content-Type"] or "application/json"
        headers["Content-Length"] = tostring(#body)
    end

    local lines = { string.format("%s %s HTTP/1.1", method, path) }
    for k, v in pairs(headers) do
        lines[#lines + 1] = string.format("%s: %s", k, v)
    end
    lines[#lines + 1] = ""
    lines[#lines + 1] = body or ""
    local raw_req = table.concat(lines, "\r\n")

    local sent, send_err = sock:send(raw_req)
    if not sent then
        sock:close()
        return nil, send_err or "send failed"
    end

    local reader = sock:receiveuntil("\r\n")
    local status_line, read_err = reader()
    if not status_line then
        sock:close()
        return nil, read_err or "no status"
    end
    local status = tonumber(status_line:match("^HTTP/%d%.%d%s+(%d+)")) or 0

    local resp_headers = {}
    while true do
        local line
        line, read_err = reader()
        if not line then
            sock:close()
            return nil, read_err or "header read failed"
        end
        if line == "" then
            break
        end
        local k, v = line:match("^([^:]+):%s*(.*)$")
        if k then
            resp_headers[k:lower()] = v
        end
    end

    local resp_body = ""
    local clen = tonumber(resp_headers["content-length"])
    if clen and clen > 0 then
        resp_body, read_err = sock:receive(clen)
        if not resp_body then
            sock:close()
            return nil, read_err or "body read failed"
        end
    else
        resp_body, read_err = sock:receive("*a")
        if not resp_body then
            resp_body = ""
        end
    end
    sock:close()
    return { status = status, body = resp_body }, nil
end

local function request(method, path, body, extra_headers)
    local last_err
    for attempt = 1, 3 do
        local res, err = request_once(method, path, body, extra_headers)
        if res then
            return res, nil
        end
        last_err = err
        if attempt < 3 and err and (
            err:find("refused", 1, true)
            or err:find("timeout", 1, true)
            or err:find("closed", 1, true)
        ) then
            ngx.sleep(0.1 * attempt)
        else
            break
        end
    end
    return nil, last_err
end

local function decode_body(res)
    if not res or not res.body or res.body == "" then
        return nil, "empty response"
    end
    local payload = cjson.decode(res.body)
    if type(payload) ~= "table" then
        return nil, "invalid json"
    end
    if tonumber(payload.code) ~= 0 then
        return nil, payload.message or "backend error"
    end
    return payload.data, nil
end

function _M.issue()
    local res, err = request("GET", "/internal/waf/slide-captcha/issue")
    if not res then
        return nil, err or "request failed"
    end
    if res.status ~= 200 then
        return nil, "backend status " .. tostring(res.status)
    end
    return decode_body(res)
end

function _M.verify(captcha_key, x, y)
    local body = cjson.encode({
        captcha_key = captcha_key,
        x = math.floor(tonumber(x) or 0),
        y = math.floor(tonumber(y) or 0),
    })
    local res, err = request("POST", "/internal/waf/slide-captcha/verify", body)
    if not res then
        return false, err or "request failed"
    end
    if res.status == 200 then
        return true, nil
    end
    return false, "verification failed"
end

return _M
