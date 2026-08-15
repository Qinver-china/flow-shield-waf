-- Human-verification (CAPTCHA) and JavaScript challenge actions.
-- Clearance is rule-scoped (triggering rule + its dimension key), not global.
local cjson = require "cjson.safe"
local util = require "waf.util"
local clearance = require "waf.clearance"
local extractor = require "waf.extractor"
local page_render = require "waf.page_render"
local js_pow = require "waf.js_pow"
local motion_trail = require "waf.motion_trail"

local _M = {}

local MOTION_TRAIL_JS = motion_trail.client_js()

local store = ngx.shared.waf_challenge

local function secret()
    local value = os.getenv("WAF_CHALLENGE_SECRET")
    if type(value) == "string" and value ~= "" then
        return value
    end
    return nil
end

local function client_ip()
    return util.client_ip()
end

local function post_arg(value)
    if type(value) == "table" then
        return value[1]
    end
    return value
end

local function motion_ok(encoded, opts)
    local ok, err = motion_trail.verify_and_store(encoded, opts)
    if ok then
        return true
    end
    if err == "motion_replay" then
        ngx.log(ngx.WARN, "waf motion: identical trail replay detected")
        return false
    end
    if err == "motion_too_short" or err == "motion_invalid" then
        ngx.log(ngx.WARN, "waf motion: trail rejected: ", err or "unknown")
        return false
    end
    return true
end

local function sign(expiry, ip)
    local sec = secret()
    if not sec then
        ngx.log(ngx.ERR, "waf challenge: WAF_CHALLENGE_SECRET is not configured")
        return nil
    end
    return util.hmac(sec, expiry .. "|" .. ip)
end

local function parse_token(raw)
    if not raw then
        return nil
    end
    local expiry, mac = raw:match("^(%d+)%.(%x+)$")
    if not expiry then
        return nil
    end
    expiry = tonumber(expiry)
    if not expiry or expiry < ngx.time() then
        return nil
    end
    if mac ~= sign(expiry, client_ip()) then
        return nil
    end
    return expiry
end

local function host_matches_request(host)
    if type(host) ~= "string" or host == "" then
        return false
    end
    local req_host = ngx.var.host or ""
    local host_only = host:match("^([^:]+)") or host
    local req_only = req_host:match("^([^:]+)") or req_host
    return host_only:lower() == req_only:lower()
end

-- Accept relative paths or same-origin absolute URLs from client JS (location.href).
local function safe_redirect(url)
    if type(url) ~= "string" or url == "" then
        return "/"
    end
    url = url:match("^%s*(.-)%s*$") or url
    if url == "" then
        return "/"
    end

    local scheme, host, rest = url:match("^(https?)://([^/?#]+)(/.*)$")
    if not scheme then
        scheme, host = url:match("^(https?)://([^/?#]+)$")
        rest = "/"
    end
    if scheme and host then
        if not host_matches_request(host) then
            return "/"
        end
        url = rest or "/"
    end

    local path = url:match("^([^?#]*)") or url
    if path == "" then
        path = "/"
        if url:sub(1, 1) == "?" or url:sub(1, 1) == "#" then
            url = "/" .. url
        end
    end
    if path:sub(1, 1) ~= "/" or path:sub(1, 2) == "//" then
        return "/"
    end
    if path:sub(1, 6) == "/.waf/" then
        return "/"
    end
    return url
end

local function captcha_prev_uri(raw)
    if type(raw) ~= "string" or raw == "" then
        raw = "/"
    end
    local path = raw:match("^([^?#]*)") or raw
    local query = raw:match("%?(.*)$")
    if not path or path == "" then
        path = "/"
    end
    if not query or query == "" then
        return path
    end
    local kept = {}
    for pair in query:gmatch("[^&]+") do
        local k = pair:match("^([^=]+)")
        if k and k ~= "waf_cap_err" and k ~= "waf_slide_err" then
            kept[#kept + 1] = pair
        end
    end
    if #kept == 0 then
        return path
    end
    return path .. "?" .. table.concat(kept, "&")
end

local function captcha_fail_redirect(prev, err_key)
    prev = captcha_prev_uri(prev)
    err_key = err_key or "waf_cap_err"
    if prev:find("?", 1, true) then
        return prev .. "&" .. err_key .. "=1"
    end
    return prev .. "?" .. err_key .. "=1"
end

local function client_return_url(args)
    local raw = post_arg(args and args.r)
    return captcha_prev_uri(safe_redirect(raw))
end

local function normalize_answer(raw)
    if raw == nil then
        return nil
    end
    if type(raw) == "table" then
        raw = raw[1]
    end
    raw = tostring(raw):match("^%s*(.-)%s*$") or ""
    if raw == "" then
        return nil
    end
    raw = raw:gsub("０", "0"):gsub("１", "1"):gsub("２", "2"):gsub("３", "3"):gsub("４", "4")
        :gsub("５", "5"):gsub("６", "6"):gsub("７", "7"):gsub("８", "8"):gsub("９", "9")
    return tonumber(raw)
end

local function html_attr(value)
    if type(value) ~= "string" then
        return ""
    end
    return value
        :gsub("&", "&amp;")
        :gsub('"', "&quot;")
        :gsub("<", "&lt;")
end

local function captcha_error_html()
    if ngx.var.arg_waf_cap_err == "1" then
        return '<div class="err">答案错误，请重新计算</div>'
    end
    return ""
end

local function captcha_session_cookie(name, value, ttl)
    local parts = {
        name .. "=" .. value,
        "Path=/",
        "Max-Age=" .. tostring(ttl or 300),
        "HttpOnly",
        "SameSite=Lax",
    }
    if ngx.var.scheme == "https" then
        parts[#parts + 1] = "Secure"
    end
    return table.concat(parts, "; ")
end

function _M.is_cleared(meta, ext)
    return clearance.is_cleared(meta, ext)
end

-- ---- JavaScript challenge (invisible PoW + fingerprint) -----------------

local JS_CHALLENGE_PAGE_HEAD = [[<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>正在验证您的浏览器…</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{text-align:center}.spin{width:44px;height:44px;border:4px solid #334155;border-top-color:#38bdf8;border-radius:50%;margin:0 auto 20px;animation:s 1s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}
p{color:#94a3b8}
.brand{margin-top:24px;color:#64748b;font-size:13px}.brand b,.brand a{color:#38bdf8}.brand a{text-decoration:none}.brand a:hover{text-decoration:underline}
</style></head>
<body><div class="box">
<div class="spin"></div>
<h3>正在验证您的浏览器…</h3>
<p>请稍候，此过程为自动完成，用于防护恶意流量。</p>
<div class="brand">由 <a href="https://fswaf.top" target="_blank" rel="noopener noreferrer"><b>流盾WAF</b></a> · Flow Shield WAF 提供防护</div>
<script>
]]

local JS_CHALLENGE_PAGE_TAIL = [[
</script>
</div></body></html>]]

local function js_deny_html(message)
    message = message or "当前请求未通过安全检查。"
    local html = [[<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>访问被拒绝</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.box{text-align:center;max-width:420px;padding:0 20px}
h3{margin:0 0 12px}p{color:#94a3b8;margin:0}
</style></head>
<body><div class="box">
<h3>访问被拒绝</h3>
<p>]] .. html_attr(message) .. [[</p>
</div></body></html>]]
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(html)
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

local function js_challenge_html(token, payload)
    local token_js = string.format("%q", token)
    local cid_js = string.format("%q", payload.cid)
    local seed_js = string.format("%q", payload.seed)
    local script = js_pow.client_script(
        token_js,
        cid_js,
        seed_js,
        payload.base_difficulty
    )
    return JS_CHALLENGE_PAGE_HEAD .. script .. JS_CHALLENGE_PAGE_TAIL
end

local function store_js_context(token, payload, ttl)
    local ctx_ttl = tonumber(ttl) or js_pow.challenge_ttl()
    if ctx_ttl < js_pow.challenge_ttl() then
        ctx_ttl = js_pow.challenge_ttl()
    end
    store:set("jsctx:" .. ngx.md5(token), cjson.encode(payload), ctx_ttl)
    return ctx_ttl
end

function _M.js_challenge(ctx, meta)
    meta = meta or {}
    if not secret() then
        ngx.log(ngx.ERR, "waf challenge: WAF_CHALLENGE_SECRET missing, skipping js challenge")
        return "continue"
    end
    local server_score = js_pow.server_suspicion_score()
    if js_pow.should_block_server(server_score) then
        return js_deny_html("自动化客户端未通过浏览器安全检查。")
    end

    local payload = js_pow.new_challenge_payload(meta, server_score)
    local ctx_ttl = js_pow.challenge_ttl()
    local expiry = ngx.time() + ctx_ttl
    local sig = sign(expiry, client_ip())
    if not sig then
        ngx.log(ngx.ERR, "waf challenge: token sign failed, skipping js challenge")
        return "continue"
    end
    local token = expiry .. "." .. sig
    store_js_context(token, payload, ctx_ttl)

    ngx.status = 503
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(js_challenge_html(token, payload))
    return ngx.exit(503)
end

local function read_js_verify_args()
    if ngx.req.get_method() == "POST" then
        ngx.req.read_body()
        return ngx.req.get_post_args() or {}
    end
    return ngx.req.get_uri_args() or {}
end

function _M.handle_js_verify(ctx)
    local args = read_js_verify_args()
    local return_url = client_return_url(args)
    local token = args.t
    if type(token) == "table" then
        token = token[1]
    end
    if not parse_token(token) then
        return _M.js_challenge(ctx, {})
    end

    local ctx_key = "jsctx:" .. ngx.md5(token)
    local raw = store:get(ctx_key)
    if not raw then
        return ngx.redirect(return_url, 302)
    end

    local payload = clearance.decode_rule_meta(raw)
    if not payload or not payload.cid or not payload.seed or not payload.base_difficulty then
        store:delete(ctx_key)
        return ngx.redirect(return_url, 302)
    end

    local nonce = args.nonce
    if type(nonce) == "table" then
        nonce = nonce[1]
    end
    if nonce == nil or nonce == "" then
        return _M.js_challenge(ctx, {
            source = payload.source,
            id = payload.rule_id,
            keys = payload.keys,
        })
    end

    local fp = args.fp
    if type(fp) == "table" then
        fp = fp[1]
    end
    local difficulty, fp_err = js_pow.effective_difficulty(payload.base_difficulty, fp)
    if not difficulty then
        store:delete(ctx_key)
        if fp_err == "bot_fp" then
            return js_deny_html("当前浏览器环境未通过安全检查。")
        end
        return _M.js_challenge(ctx, {
            source = payload.source,
            id = payload.rule_id,
            keys = payload.keys,
        })
    end

    if not js_pow.verify_pow(payload.cid, payload.seed, nonce, difficulty) then
        ngx.log(ngx.WARN, "waf js: pow verification failed")
        return _M.js_challenge(ctx, {
            source = payload.source,
            id = payload.rule_id,
            keys = payload.keys,
        })
    end

    if not motion_ok(post_arg(args.mt), { min_points = 0 }) then
        return js_deny_html("当前请求未通过行为安全检查。")
    end

    store:delete(ctx_key)
    local meta = {
        source = payload.source,
        rule_id = payload.rule_id,
        keys = payload.keys,
    }
    local ext = extractor.new()
    if not clearance.grant(meta, ctx.js_challenge_ttl or 1800, ext) then
        ngx.log(ngx.ERR, "waf js: clearance grant failed")
        return _M.js_challenge(ctx, {
            source = payload.source,
            id = payload.rule_id,
            keys = payload.keys,
        })
    end
    return ngx.redirect(return_url, 302)
end

-- ---- CAPTCHA (arithmetic, no external deps) ----------------------------

local CAPTCHA_PAGE = [[<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>数学计算验证</title>
<style>
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:#1e293b;padding:36px;border-radius:14px;width:320px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.4)}
h3{margin-top:0}.q{font-size:26px;font-weight:700;margin:18px 0;color:#38bdf8}
.err{color:#f87171;font-size:14px;margin:0 0 12px}
input{width:100%%;padding:12px;border-radius:8px;border:1px solid #334155;background:#0f172a;color:#e2e8f0;font-size:16px;box-sizing:border-box}
button{margin-top:16px;width:100%%;padding:12px;border:0;border-radius:8px;background:#38bdf8;color:#04121f;font-weight:700;font-size:16px;cursor:pointer}
.tip{color:#94a3b8;font-size:13px;margin-top:14px}
.brand{margin-top:18px;color:#64748b;font-size:12px}.brand b,.brand a{color:#38bdf8}.brand a{text-decoration:none}.brand a:hover{text-decoration:underline}
</style></head>
<body><div class="card">
<h3>请完成数学计算验证</h3>
%s
<div class="q">%d + %d = ?</div>
<form method="POST" action="/.waf/challenge-submit" id="cap-form">
<input type="hidden" name="cid" value="%s">
<input type="hidden" name="r" id="cap-r" value="">
<input type="hidden" name="mt" id="cap-mt" value="">
<input type="text" name="answer" autocomplete="off" autofocus placeholder="请输入计算结果">
<button type="submit">验证并继续</button>
</form>
<div class="tip">此验证用于确认您不是自动化程序</div>
<div class="brand">%s</div>
<script>
]] .. MOTION_TRAIL_JS .. [[
document.getElementById('cap-form').addEventListener('submit',function(){
  document.getElementById('cap-mt').value=WafMotion.pack();
  document.getElementById('cap-r').value=location.href;
});
</script>
</div></body></html>]]

local function captcha_footer_html(cfg, site, ctx, meta)
    return page_render.render_captcha_footer(cfg, site, ctx, meta)
end

function _M.captcha(cfg, site, ctx, meta)
    meta = meta or {}
    local a = math.random(1, 9)
    local b = math.random(1, 9)
    local cid = ngx.md5(ngx.now() .. math.random() .. client_ip())
    local payload = cjson.encode({
        ans = a + b,
        source = meta.source,
        rule_id = meta.id,
        keys = meta.keys,
    })
    store:set(cid, payload, 300)
    ngx.header["Set-Cookie"] = captcha_session_cookie("waf_cap", cid, 300)
    ngx.status = ngx.HTTP_OK
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(string.format(
        CAPTCHA_PAGE,
        captcha_error_html(),
        a,
        b,
        cid,
        captcha_footer_html(cfg, site, ctx, meta)
    ))
    return ngx.exit(ngx.HTTP_OK)
end

function _M.handle_captcha_verify(ctx)
    ngx.req.read_body()
    local args = ngx.req.get_post_args() or {}
    local return_url = client_return_url(args)
    local cid = args.cid or ngx.var["cookie_waf_cap"]
    local answer = normalize_answer(args.answer)

    local payload
    if cid then
        local raw = store:get(cid)
        payload = type(raw) == "string" and cjson.decode(raw) or nil
    end

    if cid and answer and payload and tonumber(payload.ans) == answer then
        if not motion_ok(post_arg(args.mt), { min_points = 0 }) then
            return ngx.redirect(captcha_fail_redirect(return_url), ngx.HTTP_SEE_OTHER)
        end
        store:delete(cid)
        local meta = {
            source = payload.source,
            rule_id = payload.rule_id,
            keys = payload.keys,
        }
        local ext = extractor.new()
        if not clearance.grant(meta, ctx.captcha_ttl or 1800, ext) then
            ngx.log(ngx.ERR, "waf captcha: clearance grant failed after valid answer")
            return ngx.redirect(captcha_fail_redirect(return_url), ngx.HTTP_SEE_OTHER)
        end
        ngx.header["Set-Cookie"] = "waf_cap=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
        return ngx.redirect(return_url, ngx.HTTP_SEE_OTHER)
    end
    return ngx.redirect(captcha_fail_redirect(return_url), ngx.HTTP_SEE_OTHER)
end

-- ---- Slide captcha (pi-captcha via FastAPI) ------------------------------

local function slide_backend()
    return require "waf.slide_backend"
end

local SLIDE_PAGE = [[<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>滑动验证</title>
<style>
*{box-sizing:border-box}
body{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:20px}
.card{background:#1e293b;padding:28px 24px 24px;border-radius:14px;width:min(100%%,360px);box-shadow:0 10px 40px rgba(0,0,0,.4)}
h3{margin:0 0 8px;text-align:center}
.sub{color:#94a3b8;font-size:13px;text-align:center;margin:0 0 10px}
.err{color:#f87171;font-size:14px;text-align:center;margin:0 0 12px;min-height:20px}
.stage{width:300px;height:220px;position:relative;border-radius:10px;overflow:hidden;background:#0f172a;border:1px solid #334155;margin:0 auto;touch-action:none;cursor:default}
.stage img#bg{display:block;width:300px;height:220px;user-select:none;-webkit-user-drag:none;pointer-events:none}
.tile-float{position:absolute;top:0;left:0;z-index:2;touch-action:none;cursor:grab;filter:drop-shadow(0 2px 6px rgba(0,0,0,.4))}
.tile-float:active{cursor:grabbing}
.drag-tip{color:#64748b;font-size:13px;text-align:center;margin:12px 0 0;min-height:18px}
.brand{margin-top:16px;color:#64748b;font-size:12px;text-align:center}.brand b,.brand a{color:#38bdf8}.brand a{text-decoration:none}.brand a:hover{text-decoration:underline}
.loading{text-align:center;color:#94a3b8;padding:40px 0}
#panel{min-height:240px}
</style></head>
<body><div class="card">
<h3>请完成滑动验证</h3>
<p class="sub">拖动拼图至缺口位置</p>
<div id="err" class="err">%s</div>
<div id="panel" class="loading">正在加载验证…</div>
<div class="brand">%s</div>
<script>
]] .. MOTION_TRAIL_JS .. [[
(function(){
var errEl=document.getElementById('err');
var panel=document.getElementById('panel');
function showErr(msg){errEl.textContent=msg||'';}
function postVerify(key,x,y,mt){
  var body=new URLSearchParams();
  body.set('key',key);
  body.set('x',String(x));
  body.set('y',String(y));
  body.set('r',location.href);
  if(mt)body.set('mt',mt);
  return fetch('/.waf/slide-captcha/verify',{method:'POST',body:body,credentials:'same-origin'})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,body:j};});});
}
function buildUI(data){
  var IMG_W=300;
  var tileX=Number(data.tile_x)||0;
  var tileY=Number(data.tile_y)||0;
  var tileW=Number(data.tile_width)||0;
  var tileH=Number(data.tile_height)||0;
  panel.className='';
  panel.innerHTML=''
    +'<div class="stage" id="stage"><img id="bg" alt="background" width="300" height="220"><img id="tile-float" class="tile-float" alt="tile" draggable="false"></div>'
    +'<p class="drag-tip" id="hint">按住拼图拖动至缺口</p>';
  var stage=document.getElementById('stage');
  var bg=document.getElementById('bg');
  var tileFloat=document.getElementById('tile-float');
  var hint=document.getElementById('hint');
  bg.src=data.image_base64;
  tileFloat.src=data.tile_base64;
  var thumbLeft=tileX;
  var minX=tileX;
  var maxX=IMG_W-tileW;
  var dragging=false;
  var startX=0;
  var startThumb=0;
  var moved=false;
  function layout(){
    tileFloat.style.width=tileW+'px';
    tileFloat.style.height=tileH+'px';
    tileFloat.style.left=Math.round(thumbLeft)+'px';
    tileFloat.style.top=Math.round(tileY)+'px';
  }
  function stageX(e){
    var r=stage.getBoundingClientRect();
    return (e.touches?e.touches[0].clientX:e.clientX)-r.left;
  }
  function setThumb(v){
    thumbLeft=Math.max(minX,Math.min(maxX,v));
    layout();
  }
  function submitVerify(){
    var pointX=Math.floor(thumbLeft+0.5);
    var pointY=Math.floor(tileY+0.5);
    showErr('');
    hint.textContent='正在验证…';
    postVerify(data.captcha_key,pointX,pointY,WafMotion.pack()).then(function(res){
      var dest=(res.body&&res.body.redirect)||'/';
      if(res.body&&res.body.ok){
        window.location.replace(dest);
        return;
      }
      showErr('验证失败，请重试');
      hint.textContent='按住拼图拖动至缺口';
      setTimeout(function(){window.location.replace(dest);},900);
    }).catch(function(){
      showErr('网络错误，请重试');
      hint.textContent='按住拼图拖动至缺口';
    });
  }
  function onDown(e){
    dragging=true;
    moved=false;
    startX=stageX(e);
    startThumb=thumbLeft;
    WafMotion.rel(stage,e);
    e.preventDefault();
  }
  function onMove(e){
    if(!dragging)return;
    var dx=stageX(e)-startX;
    if(Math.abs(dx)>2)moved=true;
    setThumb(startThumb+dx);
    WafMotion.rel(stage,e);
    e.preventDefault();
  }
  function onUp(){
    if(!dragging)return;
    dragging=false;
    if(!moved)return;
    submitVerify();
  }
  tileFloat.addEventListener('mousedown',onDown);
  tileFloat.addEventListener('touchstart',onDown,{passive:false});
  stage.addEventListener('mousedown',function(e){
    if(e.target===stage)onDown(e);
  });
  window.addEventListener('mousemove',onMove);
  window.addEventListener('touchmove',onMove,{passive:false});
  window.addEventListener('mouseup',onUp);
  window.addEventListener('touchend',onUp);
  bg.onload=layout;
  tileFloat.onload=layout;
  if(bg.complete&&tileFloat.complete)layout();
}
var SLIDE_BOOT=%s;
function bootSlide(){
  if(SLIDE_BOOT&&SLIDE_BOOT.captcha_key){buildUI(SLIDE_BOOT);return;}
  fetch('/.waf/slide-captcha/issue',{credentials:'same-origin'})
    .then(function(r){return r.json();})
    .then(function(resp){
      if(resp&&resp.ok&&resp.data){buildUI(resp.data);return;}
      showErr('加载失败，请刷新页面');panel.textContent='';
    })
    .catch(function(){showErr('加载失败，请刷新页面');panel.textContent='';});
}
bootSlide();
})();
</script>
</div></body></html>]]

local function slide_error_html()
    if ngx.var.arg_waf_slide_err == "1" then
        return "验证失败，请重试"
    end
    return ""
end

local function slide_session_cookie(name, value, ttl)
    return captcha_session_cookie(name, value, ttl)
end

function _M.slide_captcha(cfg, site, ctx, meta)
    meta = meta or {}
    local sid = ngx.md5(ngx.now() .. math.random() .. client_ip())
    local payload = cjson.encode({
        source = meta.source,
        rule_id = meta.id,
        keys = meta.keys,
    })
    store:set("slide:" .. sid, payload, 300)

    ngx.header["Set-Cookie"] = slide_session_cookie("waf_slide", sid, 300)
    ngx.status = ngx.HTTP_OK
    ngx.header["Content-Type"] = "text/html; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(string.format(
        SLIDE_PAGE,
        slide_error_html(),
        captcha_footer_html(cfg, site, ctx, meta),
        "null"
    ))
    return ngx.exit(ngx.HTTP_OK)
end

function _M.handle_slide_issue()
    local sid = ngx.var["cookie_waf_slide"]
    if not sid then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say('{"ok":false,"error":"missing session"}')
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    local raw = store:get("slide:" .. sid)
    if not raw then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say('{"ok":false,"error":"session expired"}')
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    local data, err = slide_backend().issue()
    if not data then
        ngx.log(ngx.ERR, "waf slide: issue failed: ", err or "unknown")
        ngx.status = ngx.HTTP_SERVICE_UNAVAILABLE
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say('{"ok":false,"error":"issue failed"}')
        return ngx.exit(ngx.HTTP_SERVICE_UNAVAILABLE)
    end
    ngx.header["Content-Type"] = "application/json; charset=utf-8"
    ngx.header["Cache-Control"] = "no-store"
    ngx.say(cjson.encode({ ok = true, data = data }))
    return ngx.exit(ngx.HTTP_OK)
end

function _M.handle_slide_verify(ctx)
    ngx.req.read_body()
    local args = ngx.req.get_post_args() or {}
    local return_url = client_return_url(args)
    local sid = ngx.var["cookie_waf_slide"]
    local key = post_arg(args.key)
    local x = post_arg(args.x)
    local y = post_arg(args.y)
    local mt = post_arg(args.mt)

    local payload
    if sid then
        local raw = store:get("slide:" .. sid)
        payload = type(raw) == "string" and cjson.decode(raw) or nil
    end

    if not motion_ok(mt, { min_points = 3 }) then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say(cjson.encode({ ok = false, redirect = captcha_fail_redirect(return_url, "waf_slide_err") }))
        return ngx.exit(ngx.HTTP_OK)
    end

    local ok, verr = slide_backend().verify(key, x, y)
    if ok and payload then
        store:delete("slide:" .. sid)
        local meta = {
            source = payload.source,
            rule_id = payload.rule_id,
            keys = payload.keys,
        }
        local ext = extractor.new()
        if clearance.grant(meta, ctx.captcha_ttl or 1800, ext) then
            ngx.status = ngx.HTTP_OK
            ngx.header["Set-Cookie"] = "waf_slide=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
            ngx.header["Content-Type"] = "application/json; charset=utf-8"
            ngx.say(cjson.encode({ ok = true, redirect = return_url }))
            return ngx.exit(ngx.HTTP_OK)
        end
        ngx.log(ngx.ERR, "waf slide: clearance grant failed")
        ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say(cjson.encode({ ok = false, redirect = captcha_fail_redirect(return_url, "waf_slide_err") }))
        return ngx.exit(ngx.HTTP_OK)
    end
    if ok and not payload then
        ngx.log(ngx.WARN, "waf slide: captcha ok but session missing, sid=", sid or "nil")
        verr = "session missing"
    else
        ngx.log(ngx.WARN, "waf slide: verify failed: key=", key or "nil",
            " x=", x or "nil", " y=", y or "nil", " err=", verr or "unknown")
    end
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.header["Content-Type"] = "application/json; charset=utf-8"
    ngx.say(cjson.encode({ ok = false, redirect = captcha_fail_redirect(return_url, "waf_slide_err") }))
    return ngx.exit(ngx.HTTP_OK)
end

return _M
