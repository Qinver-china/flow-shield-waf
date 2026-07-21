-- Mouse / touch motion trail capture helpers and Redis replay detection.
local cjson = require "cjson.safe"
local redis_client = require "waf.redis_client"

local _M = {}

local REDIS_KEY = "waf:motion:recent"

local function max_trails()
    return tonumber(os.getenv("MOTION_TRAIL_LIMIT")) or 500
end

local function sha256_hex(msg)
    local ok, resty_sha256 = pcall(require, "resty.sha256")
    if not ok or not resty_sha256 then
        return ngx.md5(msg)
    end
    local sha = resty_sha256:new()
    sha:update(msg)
    return sha:final()
end

local function decode_payload(encoded)
    if type(encoded) ~= "string" or encoded == "" then
        return nil, 0
    end
    local raw = ngx.decode_base64(encoded)
    if not raw then
        return nil, 0
    end
    local deltas = cjson.decode(raw)
    if type(deltas) ~= "table" then
        return nil, 0
    end
    local parts = {}
    for _, d in ipairs(deltas) do
        if type(d) == "table" and d[1] ~= nil and d[2] ~= nil and d[3] ~= nil then
            parts[#parts + 1] = string.format("%d,%d,%d", tonumber(d[1]) or 0, tonumber(d[2]) or 0, tonumber(d[3]) or 0)
        end
    end
    if #parts == 0 then
        return nil, 0
    end
    return table.concat(parts, ";"), #parts
end

function _M.point_count(encoded)
    local _, count = decode_payload(encoded)
    return count
end

function _M.hash_trail(encoded)
    local canonical = decode_payload(encoded)
    if not canonical then
        return nil
    end
    return sha256_hex(canonical)
end

function _M.verify_and_store(encoded, opts)
    opts = opts or {}
    local min_points = tonumber(opts.min_points) or 0
    local _, count = decode_payload(encoded)

    if count == 0 then
        if min_points > 0 then
            return false, "motion_too_short"
        end
        return true, nil
    end

    if count < min_points then
        return false, "motion_too_short"
    end

    -- Too little signal for replay checks; still accept.
    if count < 2 then
        return true, nil
    end

    local hash = _M.hash_trail(encoded)
    if not hash then
        return false, "motion_invalid"
    end

    local red, err = redis_client.connect()
    if not red then
        ngx.log(ngx.ERR, "waf motion: redis unavailable, skipping replay check: ", err or "unknown")
        return true, nil
    end

    local limit = max_trails() - 1
    if limit < 0 then
        limit = 0
    end

    local list, lerr = red:lrange(REDIS_KEY, 0, limit)
    if not list and lerr then
        redis_client.release(red)
        ngx.log(ngx.ERR, "waf motion: redis lrange failed: ", lerr)
        return true, nil
    end

    for _, existing in ipairs(list or {}) do
        if existing == hash then
            redis_client.release(red)
            return false, "motion_replay"
        end
    end

    local _, perr = red:lpush(REDIS_KEY, hash)
    if perr then
        redis_client.close(red)
        ngx.log(ngx.ERR, "waf motion: redis lpush failed: ", perr)
        return true, nil
    end
    red:ltrim(REDIS_KEY, 0, limit)
    redis_client.release(red)
    return true, nil
end

function _M.client_js()
    return [[
var WafMotion=(function(){
  var pts=[],t0=Date.now(),lx=-1,ly=-1,lt=0;
  function snap(x,y){
    var t=Date.now()-t0;
    if(lx>=0&&(Math.abs(x-lx)+Math.abs(y-ly))<2&&(t-lt)<20)return;
    lt=t;lx=x;ly=y;
    pts.push([t,x,y]);
    if(pts.length>150)pts.shift();
  }
  function rel(el,e){
    var r=el.getBoundingClientRect();
    var cx=(e.touches?e.touches[0].clientX:e.clientX)-r.left;
    var cy=(e.touches?e.touches[0].clientY:e.clientY)-r.top;
    snap(Math.round(cx),Math.round(cy));
  }
  document.addEventListener('mousemove',function(e){snap(e.clientX,e.clientY);},{passive:true});
  document.addEventListener('touchmove',function(e){if(e.touches&&e.touches[0])snap(e.touches[0].clientX,e.touches[0].clientY);},{passive:true});
  function pack(){
    if(!pts.length)return '';
    var o=[],pt=0,px=0,py=0,i,p;
    for(i=0;i<pts.length;i++){
      p=pts[i];
      o.push([p[0]-pt,p[1]-px,p[2]-py]);
      pt=p[0];px=p[1];py=p[2];
    }
    return btoa(unescape(encodeURIComponent(JSON.stringify(o))));
  }
  return {snap:snap,rel:rel,pack:pack,len:function(){return pts.length;}};
})();
]]
end

return _M
