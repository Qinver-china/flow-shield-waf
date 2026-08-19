-- Rule-scoped challenge clearance: after passing captcha / JS challenge, only the
-- triggering rule and its dimension key are exempt for TTL seconds.
local cjson = require "cjson.safe"
local util = require "waf.util"
local sync = require "waf.sync"

local _M = {}

local store = ngx.shared.waf_challenge

local DEFAULT_DIMS = { "ip" }

local HEADER_DIMS = {
    accept_language = "Accept-Language",
    accept_encoding = "Accept-Encoding",
    sec_ch_ua = "Sec-CH-UA",
    sec_ch_ua_platform = "Sec-CH-UA-Platform",
}

local function client_ip()
    return util.client_ip()
end

local function normalize_dims(raw)
    if type(raw) ~= "table" then
        return DEFAULT_DIMS
    end
    local dims = {}
    local seen = {}
    for _, dim in ipairs(raw) do
        if type(dim) == "string" and not seen[dim] then
            seen[dim] = true
            dims[#dims + 1] = dim
        end
    end
    if not seen.ip then
        dims[#dims + 1] = "ip"
    end
    if #dims == 0 then
        return DEFAULT_DIMS
    end
    return dims
end

local function current_dims()
    local cfg = sync.get().settings or {}
    return normalize_dims(cfg.clearance_fingerprint_dims)
end

-- ngx.req.get_headers() returns a table when a header has multiple values.
local function header_str(v)
    if v == nil then
        return ""
    end
    if type(v) == "table" then
        return table.concat(v, ",")
    end
    return tostring(v)
end

local function dim_value(dim, headers)
    if dim == "ip" then
        return client_ip() or ""
    end
    if dim == "ua" then
        return header_str(headers["User-Agent"])
    end
    local header = HEADER_DIMS[dim]
    if header then
        return header_str(headers[header])
    end
    return ""
end

local function fingerprint_signature(dims)
    local headers = ngx.req.get_headers()
    local parts = {}
    for _, dim in ipairs(dims) do
        parts[#parts + 1] = dim .. "=" .. dim_value(dim, headers)
    end
    return ngx.md5(table.concat(parts, "\0"))
end

local function key_field_str(v)
    if v == nil then
        return "-"
    end
    if type(v) == "table" then
        return table.concat(v, ",")
    end
    return tostring(v)
end

-- Build a stable signature from rule key fields (rate limit keys) or global dims.
function _M.dim_signature(spec, ext)
    local keys = spec and spec.keys
    if type(keys) == "table" and #keys > 0 then
        local parts = {}
        for _, k in ipairs(keys) do
            local field = k.field or k
            local arg = k.arg
            parts[#parts + 1] = tostring(field) .. "=" .. key_field_str(ext:get(field, arg))
        end
        return ngx.md5(table.concat(parts, "\0"))
    end
    return fingerprint_signature(current_dims())
end

local function storage_key(spec, ext)
    local source = tostring(spec.source or "rule")
    local rule_id = tostring(spec.rule_id or spec.id or "0")
    return "clr:" .. source .. ":" .. rule_id .. ":" .. _M.dim_signature(spec, ext)
end

function _M.grant(spec, ttl, ext)
    if type(spec) ~= "table" then
        return false
    end
    local ttl_val = tonumber(ttl) or 1800
    if ttl_val < 1 then
        ttl_val = 1
    end
    local key = storage_key(spec, ext)
    local ok, err = store:set(key, ngx.time(), ttl_val)
    if not ok then
        ngx.log(ngx.ERR, "waf clearance: grant failed: ", err, " key=", key)
    end
    return ok
end

function _M.is_cleared(spec, ext)
    if type(spec) ~= "table" then
        return false
    end
    return store:get(storage_key(spec, ext)) ~= nil
end

function _M.revoke(spec, ext)
    if type(spec) ~= "table" then
        return false
    end
    store:delete(storage_key(spec, ext))
    return true
end

function _M.encode_rule_meta(meta)
    return cjson.encode({
        source = meta.source,
        rule_id = meta.id,
        keys = meta.keys,
    })
end

function _M.decode_rule_meta(raw)
    if type(raw) ~= "string" or raw == "" then
        return nil
    end
    local parsed = cjson.decode(raw)
    if type(parsed) ~= "table" then
        return nil
    end
    if not parsed.source or not parsed.rule_id then
        return nil
    end
    return parsed
end

return _M
