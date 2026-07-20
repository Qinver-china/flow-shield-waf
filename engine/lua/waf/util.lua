-- Common helpers: hmac signing, hex, ip parsing, client ip resolution
local _M = {}

local str_byte = string.byte
local str_format = string.format
local tonumber = tonumber

function _M.to_hex(bin)
    if not bin then return nil end
    local t = {}
    for i = 1, #bin do
        t[i] = str_format("%02x", str_byte(bin, i))
    end
    return table.concat(t)
end

-- HMAC-SHA1 hex using the built-in ngx.hmac_sha1
function _M.hmac(secret, msg)
    return _M.to_hex(ngx.hmac_sha1(secret or "", msg or ""))
end

local function normalize_ip(ip)
    if not ip or ip == "" then
        return ""
    end
    local mapped = ip:match("^::ffff:(%d+%.%d+%.%d+%.%d+)$")
    if mapped then
        return mapped
    end
    return ip
end

local function header_value(name)
    local headers = ngx.req.get_headers()
    local v = headers[name]
    if type(v) == "table" then
        v = v[1]
    end
    if v and v ~= "" then
        return v
    end
    local var_name = "http_" .. name:lower():gsub("-", "_")
    return ngx.var[var_name]
end

local function xff_first()
    local xff = header_value("X-Forwarded-For")
    if not xff or xff == "" then
        return nil
    end
    return xff:match("^%s*([^,%s]+)")
end

local function xff_last()
    local xff = header_value("X-Forwarded-For")
    if not xff or xff == "" then
        return nil
    end
    local last
    for part in xff:gmatch("([^,%s]+)") do
        last = part
    end
    return last
end

local IP_RESOLVERS = {
    remote_addr = function()
        return ngx.var.remote_addr
    end,
    xff_first = xff_first,
    xff_last = xff_last,
    x_real_ip = function()
        return header_value("X-Real-IP")
    end,
    cf_connecting_ip = function()
        return header_value("CF-Connecting-IP")
    end,
    true_client_ip = function()
        return header_value("True-Client-IP")
    end,
    x_client_ip = function()
        return header_value("X-Client-IP")
    end,
}

-- Resolve client IP using per-site mode (ngx.ctx.waf_client_ip_source).
-- Falls back to remote_addr when the configured header is absent.
function _M.client_ip()
    local source = ngx.ctx.waf_client_ip_source or "remote_addr"
    local resolver = IP_RESOLVERS[source] or IP_RESOLVERS.remote_addr
    local ip = normalize_ip(resolver())
    if ip and ip ~= "" then
        return ip
    end
    return normalize_ip(ngx.var.remote_addr)
end

-- Convert IPv4 string to integer, nil if not IPv4
function _M.ipv4_to_int(ip)
    if not ip then return nil end
    local a, b, c, d = ip:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    if not a then return nil end
    a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    if a > 255 or b > 255 or c > 255 or d > 255 then return nil end
    return a * 16777216 + b * 65536 + c * 256 + d
end

-- Check if an IPv4 is within a CIDR (e.g. "10.0.0.0/8")
function _M.ip_in_cidr(ip, cidr)
    local net, bits = cidr:match("^([%d%.]+)/(%d+)$")
    if not net then
        return ip == cidr
    end
    bits = tonumber(bits)
    local ip_int = _M.ipv4_to_int(ip)
    local net_int = _M.ipv4_to_int(net)
    if not ip_int or not net_int then return false end
    if bits <= 0 then return true end
    if bits > 32 then return ip_int == net_int end
    local shift = 2 ^ (32 - bits)
    return math.floor(ip_int / shift) == math.floor(net_int / shift)
end

-- Private / internal IPv4 ranges maintained by Flow Shield WAF.
-- Used by ip.src.is_private rules, geo lookup short-circuit, and log ip_is_private.
function _M.is_private_ip(ip)
    if not ip then return false end
    return _M.ip_in_cidr(ip, "10.0.0.0/8")
        or _M.ip_in_cidr(ip, "172.16.0.0/12")
        or _M.ip_in_cidr(ip, "192.168.0.0/16")
        or _M.ip_in_cidr(ip, "127.0.0.0/8")
end

return _M
