#!/usr/bin/env bash
# 流盾WAF (Flow Shield WAF) 引擎 4 种防护模式 + 黑白名单 集成回归脚本。
# 前置：docker compose 已启动 (docker compose up -d)。
# 用法：bash deploy/smoke_test.sh [PANEL_URL] [ENGINE_URL] [ADMIN_USER] [ADMIN_PASS]
set -euo pipefail

PANEL="${1:-http://localhost:9000}"
ENGINE="${2:-http://localhost}"
USER="${3:-admin}"
PASS="${4:-admin888}"
DOMAIN="smoke.test.local"

req() { curl -s "$@"; }
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }

echo "==> 登录获取 token"
TOKEN=$(req -X POST "$PANEL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$USER\",\"password\":\"$PASS\"}" | \
  sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
[ -n "$TOKEN" ] || fail "登录失败"
AUTH="Authorization: Bearer $TOKEN"
pass "登录成功"

echo "==> 创建测试站点 ($DOMAIN -> httpbin)"
req -X POST "$PANEL/api/v1/sites" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"smoke\",\"domain\":\"$DOMAIN\",\"origin\":\"http://httpbin.org\"}" >/dev/null
sleep 5   # 等待 nginx reload

check_mode() {
  local mode="$1" expect="$2" ua="$3"
  # 创建一条基于 UA 的规则
  RID=$(req -X POST "$PANEL/api/v1/rules" -H "$AUTH" -H 'Content-Type: application/json' \
    -d "{\"name\":\"smoke-$mode\",\"mode\":\"$mode\",\"priority\":10,\"conditions\":{\"logic\":\"and\",\"conditions\":[{\"field\":\"http.ua\",\"op\":\"contains\",\"value\":\"$ua\"}]}}" | \
    sed -n 's/.*"id":\([0-9]*\).*/\1/p')
  sleep 4  # 等待规则同步到引擎
  CODE=$(req -o /dev/null -w '%{http_code}' -H "Host: $DOMAIN" -H "User-Agent: $ua" "$ENGINE/get")
  if [ "$CODE" = "$expect" ]; then pass "$mode 模式 -> HTTP $CODE"; else fail "$mode 期望 $expect 实得 $CODE"; fi
  req -X DELETE "$PANEL/api/v1/rules/$RID" -H "$AUTH" >/dev/null
  sleep 3
}

echo "==> 测试 4 种防护模式"
check_mode "block"        "403" "smoke-block-bot"
check_mode "js_challenge" "503" "smoke-js-bot"
check_mode "captcha"      "200" "smoke-captcha-bot"
# observe 模式应放行 (源站返回 200)
check_mode "observe"      "200" "smoke-observe-bot"

echo "==> 全部通过"

echo "==> 验证配置版本递增"
BEFORE_VER=$(req "$PANEL/api/v1/dashboard/health" -H "$AUTH" | sed -n 's/.*"version":\([0-9]*\).*/\1/p')
req -X POST "$PANEL/api/v1/rules" -H "$AUTH" -H 'Content-Type: application/json' \
  -d "{\"name\":\"smoke-version\",\"mode\":\"observe\",\"priority\":999,\"conditions\":{\"logic\":\"and\",\"conditions\":[{\"field\":\"http.ua\",\"op\":\"contains\",\"value\":\"smoke-version-bot\"}]}}" >/dev/null
sleep 4
AFTER_VER=$(req "$PANEL/api/v1/dashboard/health" -H "$AUTH" | sed -n 's/.*"version":\([0-9]*\).*/\1/p')
[ -n "$BEFORE_VER" ] && [ -n "$AFTER_VER" ] && [ "$AFTER_VER" -gt "$BEFORE_VER" ] || fail "配置版本未递增 ($BEFORE_VER -> $AFTER_VER)"
pass "配置版本递增 $BEFORE_VER -> $AFTER_VER"
