#!/usr/bin/env bash
# 容器启动阶段的统一日志与品牌展示（被 entrypoint / wait-for / startup-ready 引用）

STARTUP_LOCK_DIR="${STARTUP_LOCK_DIR:-/tmp/flowshield-startup}"

startup_init() {
  mkdir -p "$STARTUP_LOCK_DIR"
}

startup_header() {
  startup_once header '
    echo ""
    echo "[startup] ========================================"
    echo "[startup]  流盾 WAF 正在启动..."
    echo "[startup] ========================================"
  '
}

startup_step() {
  echo "[startup] [$1] $2"
}

startup_sub() {
  echo "[startup]       $1"
}

startup_warn() {
  echo "[startup] WARN: $1" >&2
}

# 同一启动阶段只打印一次（多进程并行 wait 时避免刷屏）
startup_once() {
  local key="$1"
  shift
  mkdir -p "$STARTUP_LOCK_DIR" 2>/dev/null || true
  if mkdir "${STARTUP_LOCK_DIR}/${key}.lock" 2>/dev/null; then
    eval "$@"
  fi
}

show_brand_banner() {
  cat <<'BANNER'

[startup] ========================================
[startup]
[startup]     流盾 WAF  ·  Flow Shield WAF
[startup]
[startup]     流盾 WAF，守住每一次真实访问。
[startup]
[startup]     ✓ 全部服务已就绪
[startup]
[startup]     管理面板    :9000
[startup]     WAF 防护    :80 / :443
[startup]
[startup] ========================================

BANNER
}
