-- Shared URI parsing for rule extraction and log emission.
-- Keeps http.uri.* dimensions aligned with log columns.
local _M = {}

local function path_raw()
    return ngx.var.uri or "/"
end

function _M.path()
    return path_raw()
end

function _M.request_uri()
    return ngx.var.request_uri or ""
end

function _M.query()
    return ngx.var.args
end

function _M.ext(path)
    path = path or path_raw()
    if not path or path == "" then
        return nil
    end
    return path:match("%.([%w%-]+)$")
end

function _M.depth(path)
    path = path or path_raw()
    local n = 0
    for _ in (path or ""):gmatch("[^/]+") do
        n = n + 1
    end
    return n
end

function _M.segment(path, idx)
    path = path or path_raw()
    local segs = {}
    for s in (path or ""):gmatch("[^/]+") do
        segs[#segs + 1] = s
    end
    local i = tonumber(idx or "1") or 1
    return segs[i]
end

function _M.full_url()
    return (ngx.var.scheme or "http") .. "://" .. (ngx.var.host or "") .. (ngx.var.request_uri or "")
end

function _M.query_count()
    local args = ngx.req.get_uri_args()
    if type(args) ~= "table" then
        return 0
    end
    local n = 0
    for _ in pairs(args) do
        n = n + 1
    end
    return n
end

function _M.referer()
    local ref = ngx.var.http_referer
    if not ref or ref == "" then
        return nil
    end
    return ref
end

function _M.referer_host()
    local ref = _M.referer()
    if not ref then
        return nil
    end
    return ref:match("^https?://([^/%?#:]+)")
end

return _M
