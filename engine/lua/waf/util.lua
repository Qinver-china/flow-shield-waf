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

-- TCP peer address (CDN / proxy node). Survives ngx_http_realip rewriting
-- of $remote_addr; falls back to $remote_addr when realip is unused.
function _M.tcp_ip()
    local ip = ngx.var.realip_remote_addr
    if not ip or ip == "" then
        ip = ngx.var.remote_addr
    end
    return normalize_ip(ip)
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

-- Split "a:b:c" into hextet strings; empty / malformed sides return nil.
local function split_hextets(s)
    if s == "" then
        return {}
    end
    if s:find("::", 1, true) then
        return nil
    end
    local parts = {}
    for part in (s .. ":"):gmatch("([^:]*):") do
        if part == "" then
            return nil
        end
        parts[#parts + 1] = part
    end
    return parts
end

-- Replace a trailing dotted IPv4 with two hextets (e.g. ::ffff:192.0.2.1).
local function expand_ipv4_tail(ip)
    local v4 = ip:match(":(%d+%.%d+%.%d+%.%d+)$")
    if not v4 then
        return ip
    end
    local a, b, c, d = v4:match("^(%d+)%.(%d+)%.(%d+)%.(%d+)$")
    a, b, c, d = tonumber(a), tonumber(b), tonumber(c), tonumber(d)
    if not a or a > 255 or b > 255 or c > 255 or d > 255 then
        return nil
    end
    return ip:sub(1, #ip - #v4) .. str_format("%x:%x", a * 256 + b, c * 256 + d)
end

-- Parse IPv6 (optional brackets) into eight 16-bit words.
local function ipv6_to_words(ip)
    if type(ip) ~= "string" or ip == "" then
        return nil
    end
    if ip:sub(1, 1) == "[" then
        if ip:sub(-1) ~= "]" then
            return nil
        end
        ip = ip:sub(2, -2)
    end
    local zone = ip:find("%", 1, true)
    if zone then
        ip = ip:sub(1, zone - 1)
    end
    ip = expand_ipv4_tail(ip)
    if not ip then
        return nil
    end

    local dc = ip:find("::", 1, true)
    local left, right
    if dc then
        if ip:find("::", dc + 2, true) then
            return nil
        end
        left = ip:sub(1, dc - 1)
        right = ip:sub(dc + 2)
    else
        left, right = ip, nil
    end

    local lparts = split_hextets(left)
    if not lparts then
        return nil
    end
    local rparts = {}
    if right ~= nil then
        rparts = split_hextets(right)
        if not rparts then
            return nil
        end
    end

    local n = #lparts + #rparts
    if dc then
        if n > 7 then
            return nil
        end
    elseif n ~= 8 then
        return nil
    end

    local words = {}
    local function push_parts(parts)
        for i = 1, #parts do
            local part = parts[i]
            if #part == 0 or #part > 4 or part:find("[^0-9a-fA-F]") then
                return false
            end
            words[#words + 1] = tonumber(part, 16)
        end
        return true
    end
    if not push_parts(lparts) then
        return nil
    end
    if dc then
        for _ = 1, 8 - n do
            words[#words + 1] = 0
        end
    end
    if not push_parts(rparts) then
        return nil
    end
    if #words ~= 8 then
        return nil
    end
    return words
end

local function ipv6_equal(a, b)
    local wa = ipv6_to_words(a)
    local wb = ipv6_to_words(b)
    if not wa or not wb then
        return false
    end
    for i = 1, 8 do
        if wa[i] ~= wb[i] then
            return false
        end
    end
    return true
end

local function ipv6_in_prefix(ip_words, net_words, bits)
    if bits < 0 or bits > 128 then
        return false
    end
    if bits == 0 then
        return true
    end
    local full = math.floor(bits / 16)
    for i = 1, full do
        if ip_words[i] ~= net_words[i] then
            return false
        end
    end
    local rem = bits % 16
    if rem == 0 then
        return true
    end
    local shift = 2 ^ (16 - rem)
    return math.floor(ip_words[full + 1] / shift) == math.floor(net_words[full + 1] / shift)
end

-- Check if an IP is within a CIDR (IPv4 or IPv6). Bare addresses match exactly.
function _M.ip_in_cidr(ip, cidr)
    local net, bits = cidr:match("^(.*)/(%d+)$")
    if not net then
        return ip == cidr or ipv6_equal(ip, cidr)
    end
    bits = tonumber(bits)
    local ip_int = _M.ipv4_to_int(ip)
    local net_int = _M.ipv4_to_int(net)
    if ip_int and net_int then
        if bits <= 0 then return true end
        if bits > 32 then return ip_int == net_int end
        local shift = 2 ^ (32 - bits)
        return math.floor(ip_int / shift) == math.floor(net_int / shift)
    end
    local ip6 = ipv6_to_words(ip)
    local net6 = ipv6_to_words(net)
    if not ip6 or not net6 then
        return false
    end
    return ipv6_in_prefix(ip6, net6, bits)
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
