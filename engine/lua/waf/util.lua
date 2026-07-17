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

-- Resolve client IP for rate limiting and challenge clearance.
-- Edge WAF uses the TCP peer address so clients cannot spoof X-Forwarded-For.
-- (Trusted upstream proxy support can be added later via settings.)
function _M.client_ip()
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

function _M.is_private_ip(ip)
    if not ip then return false end
    return _M.ip_in_cidr(ip, "10.0.0.0/8")
        or _M.ip_in_cidr(ip, "172.16.0.0/12")
        or _M.ip_in_cidr(ip, "192.168.0.0/16")
        or _M.ip_in_cidr(ip, "127.0.0.0/8")
end

return _M
