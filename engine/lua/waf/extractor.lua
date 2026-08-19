-- Field extractor: maps a catalog field `key` (+ optional `arg`) to the
-- concrete request value. Mirrors the backend field catalog (single source
-- of truth). Body/JSON/multipart fields are read lazily and cached per request.
local cjson = require "cjson.safe"
local util = require "waf.util"
local uri_parse = require "waf.uri_parse"
local geo_lookup = require "waf.geo_lookup"

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

-- Only the first 64KiB is copied into Lua. Larger bodies stay in Nginx temp
-- files so upload traffic does not pin worker memory for regex matching.
local BODY_INSPECT_MAX = 65536

local function is_multipart()
    local ct = ngx.var.content_type
    return type(ct) == "string" and ct:find("multipart/form-data", 1, true)
end

function _M:_inspect()
    if self.cache.inspect ~= nil then
        return self.cache.inspect
    end
    local sync = require "waf.sync"
    local ins = ((sync.get() or {}).settings or {}).inspect
    if type(ins) ~= "table" then
        -- Missing flags (old config): keep previous behavior if a field is read.
        self.cache.inspect = { body = true, upload = true }
    else
        self.cache.inspect = {
            body = ins.body == true,
            upload = ins.upload == true,
        }
    end
    return self.cache.inspect
end

-- True when ngx.req.get_post_args() would parse a large multipart into Lua.
-- Chunked multipart (no Content-Length) is treated as large.
function _M:_large_multipart()
    if not is_multipart() then
        return false
    end
    local n = tonumber(ngx.var.content_length)
    if not n then
        return true
    end
    return n > BODY_INSPECT_MAX
end

local function match_upload_filename(body)
    if type(body) ~= "string" then
        return nil
    end
    local quoted = body:match('filename="([^"]*)"')
    if quoted then
        return quoted
    end
    for star, token in body:gmatch("filename(%*?)%=([^%s;]+)") do
        if star ~= "*" then
            return token
        end
    end
    return nil
end

function _M:_body_prefix()
    if self.cache.body_prefix ~= nil then
        if self.cache.body_prefix == false then
            return nil
        end
        return self.cache.body_prefix
    end
    ngx.req.read_body()
    local data = ngx.req.get_body_data()
    if type(data) == "string" then
        if #data > BODY_INSPECT_MAX then
            data = data:sub(1, BODY_INSPECT_MAX)
        end
        self.cache.body_prefix = data
        return data
    end
    local fname = ngx.req.get_body_file()
    if type(fname) == "string" and fname ~= "" then
        local f = io.open(fname, "rb")
        if f then
            local chunk = f:read(BODY_INSPECT_MAX)
            f:close()
            if type(chunk) == "string" and chunk ~= "" then
                self.cache.body_prefix = chunk
                return chunk
            end
        else
            ngx.log(ngx.ERR, "waf extractor: cannot open client body file")
        end
    end
    self.cache.body_prefix = false
    return nil
end

function _M:_body()
    return self:_body_prefix()
end

function _M:_post_args()
    if self.cache.post_args ~= nil then
        return self.cache.post_args
    end
    if not self:_inspect().body then
        self.cache.post_args = {}
        return self.cache.post_args
    end
    -- Full multipart parse would pin worker RAM; form fields stay empty.
    -- http.body.raw / json still use the 64KiB prefix.
    if self:_large_multipart() then
        self.cache.post_args = {}
        return self.cache.post_args
    end
    ngx.req.read_body()
    local cl = tonumber(ngx.var.content_length)
    local spilled = ngx.req.get_body_file()
    local data = ngx.req.get_body_data()
    local too_big = (cl and cl > BODY_INSPECT_MAX)
        or (type(data) == "string" and #data > BODY_INSPECT_MAX)
        or (type(spilled) == "string" and spilled ~= "")
    if too_big then
        local prefix = self:_body_prefix()
        if type(prefix) == "string" and prefix ~= "" then
            self.cache.post_args = ngx.decode_args(prefix, 100) or {}
        else
            self.cache.post_args = {}
        end
        return self.cache.post_args
    end
    local args = ngx.req.get_post_args()
    self.cache.post_args = args or {}
    return self.cache.post_args
end

function _M:_json()
    if self.cache.json ~= nil then
        return self.cache.json or nil
    end
    if not self:_inspect().body then
        self.cache.json = false
        return nil
    end
    local body = self:_body_prefix()
    self.cache.json = body and cjson.decode(body) or false
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
    elseif field == "ip.tcp" then
        if not self.cache.tcp_ip then self.cache.tcp_ip = util.tcp_ip() end
        return self.cache.tcp_ip
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

    -- geo (optional; geoip2 vars when configured — only read when rules reference geo.*)
    elseif field == "geo.country" then
        return geo_lookup.field(self, "country")
    elseif field == "geo.region" then
        return geo_lookup.field(self, "region")
    elseif field == "geo.city" then
        return geo_lookup.field(self, "city")
    elseif field == "geo.asn" then
        return geo_lookup.field(self, "asn")
    elseif field == "geo.isp" then
        return geo_lookup.field(self, "isp")

    -- request line / method / host
    elseif field == "http.method" then
        return ngx.req.get_method()
    elseif field == "http.host" then
        return ngx.var.host
    elseif field == "http.url" then
        return uri_parse.full_url()
    elseif field == "http.request_uri" then
        return uri_parse.request_uri()

    -- url / path
    elseif field == "http.uri.path" then
        return uri_parse.path()
    elseif field == "http.uri.segment" then
        return uri_parse.segment(nil, arg)
    elseif field == "http.uri.ext" then
        return uri_parse.ext()
    elseif field == "http.uri.depth" then
        return uri_parse.depth()
    elseif field == "http.uri.query" then
        return uri_parse.query()

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
        if not self:_inspect().body then
            return nil
        end
        return self:_body_prefix()
    elseif field == "http.body.size" then
        return tonumber(ngx.var.content_length) or (self:_body_prefix() and #self:_body_prefix()) or 0
    elseif field == "http.body.form" then
        local v = self:_post_args()[arg]
        if type(v) == "table" then return table.concat(v, ",") end
        return v
    elseif field == "http.body.json" then
        local v = json_path(self:_json(), arg)
        if type(v) == "table" then return cjson.encode(v) end
        return v
    elseif field == "http.upload.filename" then
        if not self:_inspect().upload or not is_multipart() then
            return nil
        end
        return match_upload_filename(self:_body_prefix())
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

    -- ua parsing (log stats: ua_family / ua_os)
    elseif field == "ua.family" then
        if self.cache.ua_family ~= nil then
            return self.cache.ua_family
        end
        local ua_parse = require "waf.ua_parse"
        local sync = require "waf.sync"
        self.cache.ua_family = ua_parse.family(
            self:get("http.ua"),
            sync.get(),
            self,
            self.cache.site_id
        )
        return self.cache.ua_family
    elseif field == "ua.os" then
        if self.cache.ua_os ~= nil then
            return self.cache.ua_os
        end
        local ua_parse = require "waf.ua_parse"
        self.cache.ua_os = ua_parse.os(self:get("http.ua"))
        return self.cache.ua_os

    -- bot identification
    elseif field == "bot.name" then
        local bot_mod = require "waf.bot"
        local sync = require "waf.sync"
        return bot_mod.resolve_name(sync.get(), self, self.cache.site_id)
    elseif field == "bot.category" then
        local bot_mod = require "waf.bot"
        local sync = require "waf.sync"
        return bot_mod.resolve_categories(sync.get(), self, self.cache.site_id)
    elseif field == "bot.is_known" then
        local bot_mod = require "waf.bot"
        local sync = require "waf.sync"
        local match = bot_mod.identify(sync.get(), self, self.cache.site_id)
        return match ~= nil
    end

    return nil
end

return _M
