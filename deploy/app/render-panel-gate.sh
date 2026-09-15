#!/usr/bin/env bash
# Render nginx snippets that gate the admin panel behind PANEL_ENTRANCE.
# Empty / unset PANEL_ENTRANCE → unlocked (legacy: unauthenticated users see /login).
#
# When enabled:
#   - Login page and login APIs require the entrance cookie (visited /{entrance}).
#   - Already-logged-in browsers carry waf_panel_session (set by FastAPI) and skip the entrance.
set -euo pipefail

MAP_PATH="${PANEL_GATE_MAP:-/etc/nginx/http.d/panel-gate-map.conf}"
CHECK_PATH="${PANEL_GATE_CHECK:-/etc/nginx/snippets/panel-gate-check.conf}"
AUTH_CHECK_PATH="${PANEL_AUTH_CHECK:-/etc/nginx/snippets/panel-auth-check.conf}"
LOC_PATH="${PANEL_GATE_LOCATIONS:-/etc/nginx/http.d/panel-gate-locations.conf}"

RESERVED='login dashboard sites certificates rules blacklist whitelist ip-groups exceptions ratelimit bots logs alerts ai-guard settings api assets brand health favicon.png favicon.ico index.html docs redoc openapi.json openapi.yaml'

normalize_entrance() {
  local raw="${1-}"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  raw="${raw#/}"
  raw="${raw%/}"
  printf '%s' "$raw"
}

write_unlocked() {
  mkdir -p "$(dirname "$MAP_PATH")" "$(dirname "$CHECK_PATH")" "$(dirname "$AUTH_CHECK_PATH")" "$(dirname "$LOC_PATH")"
  cat >"$MAP_PATH" <<'EOF'
# panel security entrance disabled
map $host $panel_gate_ok {
    default 1;
}
map $host $panel_session_ok {
    default 1;
}
EOF
  : >"$CHECK_PATH"
  : >"$AUTH_CHECK_PATH"
  : >"$LOC_PATH"
}

entrance="$(normalize_entrance "${PANEL_ENTRANCE-}")"

if [[ -z "$entrance" ]]; then
  write_unlocked
  echo "[startup] 面板安全入口未设置，未登录访问保持直接进入登录页"
  exit 0
fi

if [[ ! "$entrance" =~ ^[A-Za-z0-9_-]{4,64}$ ]]; then
  echo "ERROR: PANEL_ENTRANCE 无效：仅允许 4–64 位字母、数字、下划线或连字符（也可留空关闭）" >&2
  exit 1
fi

for reserved in $RESERVED; do
  if [[ "$entrance" == "$reserved" ]]; then
    echo "ERROR: PANEL_ENTRANCE 不能使用保留路径：${reserved}" >&2
    exit 1
  fi
done

secret="${JWT_SECRET-}"
if [[ -z "$secret" ]]; then
  echo "ERROR: 已设置 PANEL_ENTRANCE 时必须同时提供 JWT_SECRET，才能签发入口 Cookie" >&2
  exit 1
fi

# 镜像里通常没有 openssl CLI，用已安装的 python3 计算 HMAC
hmac_sha256_hex() {
  local key="$1"
  local data="$2"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import hashlib,hmac,sys; print(hmac.new(sys.argv[1].encode(), sys.argv[2].encode(), hashlib.sha256).hexdigest())' "$key" "$data"
    return
  fi
  if command -v openssl >/dev/null 2>&1; then
    printf '%s' "$data" | openssl dgst -sha256 -hmac "$key" -hex | awk '{print $NF}'
    return
  fi
  echo "ERROR: 需要 python3 或 openssl 才能签发入口 Cookie" >&2
  return 1
}

gate_token="$(hmac_sha256_hex "$secret" "panel_entrance:${entrance}")"
session_token="$(hmac_sha256_hex "$secret" "panel_session")"
if [[ -z "$gate_token" || ${#gate_token} -lt 32 || -z "$session_token" || ${#session_token} -lt 32 ]]; then
  echo "ERROR: 无法计算面板入口 Cookie 签名" >&2
  exit 1
fi

mkdir -p "$(dirname "$MAP_PATH")" "$(dirname "$CHECK_PATH")" "$(dirname "$AUTH_CHECK_PATH")" "$(dirname "$LOC_PATH")"

cat >"$MAP_PATH" <<EOF
map \$cookie_waf_panel_gate \$panel_gate_ok {
    default 0;
    "${gate_token}" 1;
}
map \$cookie_waf_panel_session \$panel_session_ok {
    default 0;
    "${session_token}" 1;
}
map \$panel_gate_ok\$panel_session_ok \$panel_app_ok {
    default 0;
    01 1;
    10 1;
    11 1;
}
EOF

# 登录页 / 登录接口：只认安全入口 Cookie
cat >"$CHECK_PATH" <<'EOF'
if ($panel_gate_ok = 0) {
    return 404;
}
EOF

# 已登录（会话 Cookie）或已走过入口均可访问业务页与 API
cat >"$AUTH_CHECK_PATH" <<'EOF'
if ($panel_app_ok = 0) {
    return 404;
}
EOF

# add_header + return 需要 always，否则 302 不会带上 Set-Cookie
cat >"$LOC_PATH" <<EOF
location = /${entrance} {
    add_header Set-Cookie "waf_panel_gate=${gate_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800" always;
    return 302 /login;
}
location = /${entrance}/ {
    add_header Set-Cookie "waf_panel_gate=${gate_token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=604800" always;
    return 302 /login;
}
EOF

echo "[startup] 面板安全入口已启用：/${entrance} （登录页须走入口；已登录会话可直接访问面板）"
