-- Field extractor: maps a catalog field `key` (+ optional `arg`) to the
-- concrete request value. Mirrors the backend field catalog (single source
-- of truth). Body/JSON/multipart fields are read lazily and cached per request.
local cjson = require "cjson.safe"
local util = require "waf.util"

local _M = {}
_M.__index = _M

-- ---- lazy helpers -------------------------------------------------------

function _M.new()
    return setmetatable({
        cache = {},
        _trace_depth = 0,
        _trace = nil,
    }, _M)
end

-- ---- evaluation trace: record fields actually read during rule matching ----

local function trace_key(field, arg)
    if arg and arg ~= "" then
        return field .. "|" .. tostring(arg)
    end
    return field
end

function _M:trace_begin()
    self._trace_depth = (self._trace_depth or 0) + 1
    if self._trace_depth == 1 then
        self._trace = {}
    end
end

function _M:trace_end()
    if (self._trace_depth or 0) <= 0 then
        return nil
    end
    self._trace_depth = self._trace_depth - 1
    if self._trace_depth > 0 then
        return nil
    end
    local trace = self._trace
    self._trace = nil
    return trace
end

function _M:trace_active()
    return (self._trace_depth or 0) > 0
end

function _M:_trace_record(field, arg, value)
    if not self:trace_active() then
        return
    end
    self._trace[trace_key(field, arg)] = {
        field = field,
        arg = arg,
        value = value,
    }
end

function _M:trace_get(field, arg)
    if not self._trace then
        return nil
    end
    local item = self._trace[trace_key(field, arg)]
    return item and item.value
end

function _M:_uri_args()
    if self.cache.uri_args == nil then
        self.cache.uri_args = ngx.req.get_uri_args() or {}
    end
    return self.cache.uri_args
end

function _M:_headers()
    if self.cache.headers == nil then
        self.cache.headers = ngx.req.get_headers() or {}
    end
    return self.cache.headers
end

function _M:_cookies()
    if self.cache.cookies == nil then
        local map = {}
        local raw = ngx.var.http_cookie
        if raw then
            for k, v in raw:gmatch("([^%s;=]+)=([^;]*)") do
                map[k] = v
            end
        end
        self.cache.cookies = map
    end
    return self.cache.cookies
end

function _M:_body()
    if self.cache.body == nil then
        ngx.req.read_body()
        self.cache.body = ngx.req.get_body_data() or false
    end
    return self.cache.body or nil
end

function _M:_post_args()
    if self.cache.post_args == nil then
        ngx.req.read_body()
        local args = ngx.req.get_post_args()
        self.cache.post_args = args or {}
    end
    return self.cache.post_args
end

function _M:_json()
    if self.cache.json == nil then
        local body = self:_body()
        self.cache.json = body and cjson.decode(body) or false
    end
    return self.cache.json or nil
end

local function json_path(obj, path)
    if not obj or not path then return nil end
    local cur = obj
    for part in path:gmatch("[^%.]+") do
        if type(cur) ~= "table" then return nil end
        local idx = tonumber(part)
        cur = cur[part]
        if cur == nil and idx then cur = obj[idx] end
        if cur == nil then return nil end
    end
    return cur
end

local function count(t)
    local n = 0
    for _ in pairs(t or {}) do n = n + 1 end
    return n
end

local function header_val(h, name)
    local v = h[name]
    if type(v) == "table" then return table.concat(v, ",") end
    return v
end

-- ---- main dispatch ------------------------------------------------------

function _M:get(field, arg)
    local value = self:_resolve(field, arg)
    self:_trace_record(field, arg, value)
    return value
end

function _M:_resolve(field, arg)
    -- client & network
    if field == "ip.src" then
        if not self.cache.ip then self.cache.ip = util.client_ip() end
        return self.cache.ip
    elseif field == "ip.src.is_private" then
        if not self.cache.ip then self.cache.ip = util.client_ip() end
        return util.is_private_ip(self.cache.ip)
    elseif field == "net.src_port" then
        return tonumber(ngx.var.remote_port)
    elseif field == "net.dst_port" then
        return tonumber(ngx.var.server_port)
    elseif field == "net.scheme" then
        return ngx.var.scheme
    elseif field == "http.version" then
        return ngx.req.http_version()

    -- geo / threat intel (optional; from geoip2 vars if configured)
    elseif field == "geo.country" then
        return ngx.var.geoip2_country or ngx.var.http_cf_ipcountry
    elseif field == "geo.region" then
        return ngx.var.geoip2_region
    elseif field == "geo.city" then
        return ngx.var.geoip2_city
    elseif field == "geo.asn" then
        return tonumber(ngx.var.geoip2_asn)
    elseif field == "geo.isp" then
        return ngx.var.geoip2_isp
    elseif field == "geo.ip_type" then
        return ngx.var.geoip2_ip_type

    -- request line / method / host
    elseif field == "http.method" then
        return ngx.req.get_method()
    elseif field == "http.host" then
        return ngx.var.host
    elseif field == "http.url" then
        return (ngx.var.scheme or "http") .. "://" .. (ngx.var.host or "") .. (ngx.var.request_uri or "")
    elseif field == "http.request_uri" then
        return ngx.var.request_uri

    -- url / path
    elseif field == "http.uri.path" then
        return ngx.var.uri
    elseif field == "http.uri.segment" then
        local segs = {}
        for s in (ngx.var.uri or ""):gmatch("[^/]+") do segs[#segs + 1] = s end
        local idx = tonumber(arg or "1") or 1
        return segs[idx]
    elseif field == "http.uri.ext" then
        return (ngx.var.uri or ""):match("%.([%a%d]+)$")
    elseif field == "http.uri.depth" then
        local n = 0
        for _ in (ngx.var.uri or ""):gmatch("[^/]+") do n = n + 1 end
        return n
    elseif field == "http.uri.query" then
        return ngx.var.args

    -- query args
    elseif field == "http.query" then
        local v = self:_uri_args()[arg]
        if type(v) == "table" then return table.concat(v, ",") end
        return v
    elseif field == "http.query.count" then
        return count(self:_uri_args())

    -- headers
    elseif field == "http.header" then
        return header_val(self:_headers(), arg)
    elseif field == "http.header.count" then
        return count(self:_headers())
    elseif field == "http.ua" then
        return ngx.var.http_user_agent
    elseif field == "http.referer" then
        return ngx.var.http_referer
    elseif field == "http.content_type" then
        return ngx.var.content_type
    elseif field == "http.content_length" then
        return tonumber(ngx.var.content_length)
    elseif field == "http.accept" then
        return header_val(self:_headers(), "Accept")
    elseif field == "http.accept_language" then
        return header_val(self:_headers(), "Accept-Language")
    elseif field == "http.accept_encoding" then
        return header_val(self:_headers(), "Accept-Encoding")
    elseif field == "http.origin" then
        return header_val(self:_headers(), "Origin")
    elseif field == "http.xff" then
        return header_val(self:_headers(), "X-Forwarded-For")
    elseif field == "http.range" then
        return header_val(self:_headers(), "Range")
    elseif field == "http.has_auth" then
        return header_val(self:_headers(), "Authorization") ~= nil

    -- cookies
    elseif field == "http.cookie" then
        return self:_cookies()[arg]
    elseif field == "http.cookie_raw" then
        return ngx.var.http_cookie
    elseif field == "http.cookie.count" then
        return count(self:_cookies())

    -- body / post / json / upload
    elseif field == "http.body.raw" then
        return self:_body()
    elseif field == "http.body.size" then
        return tonumber(ngx.var.content_length) or (self:_body() and #self:_body()) or 0
    elseif field == "http.body.form" then
        local v = self:_post_args()[arg]
        if type(v) == "table" then return table.concat(v, ",") end
        return v
    elseif field == "http.body.json" then
        local v = json_path(self:_json(), arg)
        if type(v) == "table" then return cjson.encode(v) end
        return v
    elseif field == "http.upload.filename" then
        local ct = ngx.var.content_type
        if ct and ct:find("multipart/form%-data") then
            local body = self:_body()
            return body and body:match('filename="([^"]+)"') or nil
        end
        return nil
    elseif field == "http.upload.ext" then
        local fn = self:get("http.upload.filename")
        return fn and fn:match("%.([%a%d]+)$") or nil

    -- tls
    elseif field == "tls.version" then
        return ngx.var.ssl_protocol
    elseif field == "tls.cipher" then
        return ngx.var.ssl_cipher
    elseif field == "tls.sni" then
        return ngx.var.ssl_server_name
    elseif field == "tls.ja3" then
        return ngx.var.http_ssl_ja3  -- requires external module

    -- derived
    elseif field == "derived.args_count" then
        return count(self:_uri_args()) + count(self:_post_args())
    elseif field == "derived.time.hour" then
        return tonumber(os.date("%H"))
    elseif field == "derived.time.weekday" then
        return tonumber(os.date("%w"))
    elseif field == "derived.fingerprint" then
        if not self.cache.ip then self.cache.ip = util.client_ip() end
        return util.hmac("fp", (self.cache.ip or "") .. "|" .. (ngx.var.http_user_agent or ""))
    end

    return nil
end

return _M
