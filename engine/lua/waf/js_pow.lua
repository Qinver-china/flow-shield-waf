-- Adaptive proof-of-work and suspicion scoring for invisible JS challenges.
local util = require "waf.util"
local motion_trail = require "waf.motion_trail"

local _M = {}

local BLOCK_SCORE = 60
local MIN_DIFFICULTY = 3
local MAX_DIFFICULTY = 7
local CHALLENGE_TTL = 300

local BOT_UA_PATTERNS = {
    "bot", "crawler", "spider", "curl", "wget", "python%-requests",
    "scrapy", "httpclient", "java/", "go%-http", "libwww",
}

local function sha256_hex(msg)
    local ok, resty_sha256 = pcall(require, "resty.sha256")
    if not ok then
        ngx.log(ngx.ERR, "waf js_pow: resty.sha256 unavailable")
        return nil
    end
    local sha = resty_sha256:new()
    if not sha or not sha:update(msg or "") then
        return nil
    end
    local digest = sha:final()
    if not digest then
        return nil
    end
    return util.to_hex(digest)
end

function _M.count_leading_zero_hex(hex)
    if type(hex) ~= "string" then
        return 0
    end
    local n = 0
    for i = 1, #hex do
        if hex:sub(i, i) == "0" then
            n = n + 1
        else
            break
        end
    end
    return n
end

function _M.verify_pow(cid, seed, nonce, difficulty)
    if not cid or not seed or nonce == nil or not difficulty then
        return false
    end
    local msg = tostring(cid) .. ":" .. tostring(seed) .. ":" .. tostring(nonce)
    local hash = sha256_hex(msg)
    if not hash then
        return false
    end
    return _M.count_leading_zero_hex(hash) >= tonumber(difficulty)
end

function _M.server_suspicion_score()
    local score = 0
    local ua = (ngx.var.http_user_agent or ""):lower()
    if ua == "" then
        score = score + 30
    end
    for _, pat in ipairs(BOT_UA_PATTERNS) do
        if ua:find(pat, 1, true) then
            score = score + 40
            break
        end
    end
    if not ngx.var.http_accept or ngx.var.http_accept == "" then
        score = score + 10
    end
    if not ngx.var.http_accept_language or ngx.var.http_accept_language == "" then
        score = score + 15
    end
    local dest = ngx.var.http_sec_fetch_dest or ""
    if dest ~= "" and dest ~= "document" and dest ~= "empty" and dest ~= "iframe" then
        score = score + 10
    end
    return score
end

function _M.should_block_server(score)
    return (tonumber(score) or 0) >= BLOCK_SCORE
end

function _M.base_difficulty_from_server_score(score)
    score = tonumber(score) or 0
    if score < 10 then
        return MIN_DIFFICULTY
    end
    if score < 25 then
        return MIN_DIFFICULTY + 1
    end
    if score < 40 then
        return MIN_DIFFICULTY + 2
    end
    return MIN_DIFFICULTY + 3
end

function _M.effective_difficulty(base, fp_score)
    base = tonumber(base) or MIN_DIFFICULTY
    fp_score = tonumber(fp_score)
    if fp_score == nil then
        return nil, "missing_fp"
    end
    if fp_score >= BLOCK_SCORE then
        return nil, "bot_fp"
    end
    local extra = math.floor(fp_score / 25)
    local difficulty = base + extra
    if difficulty < base then
        difficulty = base
    end
    if difficulty < MIN_DIFFICULTY then
        difficulty = MIN_DIFFICULTY
    end
    if difficulty > MAX_DIFFICULTY then
        difficulty = MAX_DIFFICULTY
    end
    return difficulty
end

function _M.new_challenge_payload(meta, server_score)
    meta = meta or {}
    return {
        source = meta.source,
        rule_id = meta.id,
        keys = meta.keys,
        cid = ngx.md5(table.concat({
            tostring(ngx.now()),
            tostring(math.random()),
            util.client_ip(),
            tostring(meta.id or "0"),
        }, "|")),
        seed = ngx.md5(table.concat({
            tostring(ngx.now()),
            tostring(math.random()),
            tostring(meta.id or "0"),
        }, "|")),
        base_difficulty = _M.base_difficulty_from_server_score(server_score),
        server_score = server_score,
    }
end

function _M.challenge_ttl()
    return CHALLENGE_TTL
end

function _M.client_script(token_js, cid_js, seed_js, base_difficulty)
    return motion_trail.client_js() .. [[
(function(){
  var token=]] .. token_js .. [[;
  var cid=]] .. cid_js .. [[;
  var seed=]] .. seed_js .. [[;
  var baseDifficulty=]] .. tostring(base_difficulty) .. [[;

  function fingerprintScore(){
    var s=0;
    if(navigator.webdriver)s+=100;
    try{
      var c=document.createElement("canvas");
      var x=c.getContext("2d");
      x.fillText("fs",2,2);
      var d=x.getImageData(0,0,1,1).data;
      var blank=true;
      for(var i=0;i<d.length;i++){if(d[i]!==0){blank=false;break;}}
      if(blank)s+=35;
    }catch(e){}
    try{
      var gl=document.createElement("canvas").getContext("webgl");
      if(gl){
        var ext=gl.getExtension("WEBGL_debug_renderer_info");
        if(ext){
          var r=(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)||"").toLowerCase();
          if(r.indexOf("swiftshader")>=0||r.indexOf("llvmpipe")>=0)s+=60;
        }
      }
    }catch(e){}
    if(/Chrome/i.test(navigator.userAgent)&&!window.chrome)s+=30;
    if(!navigator.plugins||navigator.plugins.length===0)s+=25;
    if(!navigator.languages||navigator.languages.length===0)s+=20;
    if(!screen.width||!screen.height)s+=40;
    if(window.cdc_adoQpoasnfa76pfcZLmcfl_Array||window.__webdriver_evaluate||window.__selenium_unwrapped)s+=80;
    return s;
  }

  function leadingZeros(hash,n){
    for(var i=0;i<n;i++){if(hash.charAt(i)!=="0")return false;}
    return true;
  }

  function rotr(n,x){return (x>>>n)|(x<<(32-n));}
  function sha256hex(msg){
    var K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    var i,bytes=new TextEncoder().encode(msg),bitLen=bytes.length*8,w=new Array(64);
    var h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a,h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;
    var padded=new Uint8Array(((bytes.length+9+63)>>6)<<6);
    padded.set(bytes);padded[bytes.length]=0x80;
    new DataView(padded.buffer).setUint32(padded.length-4,bitLen,false);
    for(var off=0;off<padded.length;off+=64){
      for(i=0;i<16;i++)w[i]=new DataView(padded.buffer).getUint32(off+i*4,false);
      for(i=16;i<64;i++){
        var s0=rotr(7,w[i-15])^rotr(18,w[i-15])^(w[i-15]>>>3);
        var s1=rotr(17,w[i-2])^rotr(19,w[i-2])^(w[i-2]>>>10);
        w[i]=(w[i-16]+s0+w[i-7]+s1)|0;
      }
      var a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,hh=h7,t1,t2;
      for(i=0;i<64;i++){
        s1=rotr(6,e)^rotr(11,e)^rotr(25,e);
        t1=(hh+s1+((e&f)^(~e&g))+K[i]+w[i])|0;
        s0=rotr(2,a)^rotr(13,a)^rotr(22,a);
        t2=(s0+((a&b)^(a&c)^(b&c)))|0;
        hh=g;g=f;f=e;e=(d+t1)|0;d=c;c=b;b=a;a=(t1+t2)|0;
      }
      h0=(h0+a)|0;h1=(h1+b)|0;h2=(h2+c)|0;h3=(h3+d)|0;h4=(h4+e)|0;h5=(h5+f)|0;h6=(h6+g)|0;h7=(h7+hh)|0;
    }
    return [h0,h1,h2,h3,h4,h5,h6,h7].map(function(v){
      return ("00000000"+(v>>>0).toString(16)).slice(-8);
    }).join("");
  }

  function solvePow(difficulty){
    var nonce=0;
    while(nonce<50000000){
      var hash=sha256hex(cid+":"+seed+":"+nonce);
      if(leadingZeros(hash,difficulty))return nonce;
      nonce++;
    }
    return null;
  }

  function submit(nonce,fp){
    var dest=location.href;
    var body="t="+encodeURIComponent(token)
      +"&r="+encodeURIComponent(dest)
      +"&nonce="+encodeURIComponent(String(nonce))
      +"&fp="+encodeURIComponent(String(fp))
      +"&mt="+encodeURIComponent(WafMotion.pack());
    fetch("/.waf/js-verify",{
      method:"POST",
      headers:{"Content-Type":"application/x-www-form-urlencoded"},
      body:body,
      credentials:"same-origin",
      redirect:"follow"
    }).then(function(resp){
      if(resp.redirected){location.href=resp.url;return;}
      location.href=dest;
    }).catch(function(){location.href=dest;});
  }

  function run(){
    var fp=fingerprintScore();
    if(fp>=60){
      document.querySelector(".box h3").textContent="访问被拒绝";
      document.querySelector(".box p").textContent="当前环境未通过浏览器安全检查。";
      document.querySelector(".spin").style.display="none";
      return;
    }
    var extra=Math.floor(fp/25);
    var difficulty=baseDifficulty+extra;
    if(difficulty<baseDifficulty)difficulty=baseDifficulty;
    if(difficulty>7)difficulty=7;
  setTimeout(function(){
    var nonce=solvePow(difficulty);
    if(nonce===null){
      document.querySelector(".box p").textContent="验证超时，请刷新页面重试。";
      return;
    }
    submit(nonce,fp);
  },0);
  }

  run();
})();
]]
end

return _M
