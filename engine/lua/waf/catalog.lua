-- Loads the field catalog JSON (generated from the backend single source of
-- truth via `python -m app.fields.export`). Used to validate that rule
-- conditions reference known fields, keeping the engine extractor in parity
-- with the backend catalog.
local cjson = require "cjson.safe"

local _M = {}

local PATH = "/etc/nginx/lua/waf/fields_catalog.json"
local _fields = {}
local _loaded = false

function _M.load()
    local f = io.open(PATH, "r")
    if not f then
        ngx.log(ngx.ERR, "waf catalog: file not found: ", PATH)
        return false
    end
    local content = f:read("*a")
    f:close()

    local data = cjson.decode(content)
    if not data or not data.fields then
        ngx.log(ngx.ERR, "waf catalog: invalid json")
        return false
    end

    local m = {}
    local n = 0
    for _, fld in ipairs(data.fields) do
        m[fld.key] = fld
        n = n + 1
    end
    _fields = m
    _loaded = true
    ngx.log(ngx.NOTICE, "waf catalog: loaded ", n, " fields")
    return true
end

function _M.is_valid(key)
    return _fields[key] ~= nil
end

function _M.meta(key)
    return _fields[key]
end

function _M.loaded()
    return _loaded
end

return _M
