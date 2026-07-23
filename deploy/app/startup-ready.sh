#!/usr/bin/env bash
# 全部子进程就绪后做一次健康检查并展示品牌（supervisord 一次性任务）
set -euo pipefail

# shellcheck source=/opt/flowshield/startup-log.sh
source /opt/flowshield/startup-log.sh

WAIT_MAX="${STARTUP_READY_MAX_SEC:-120}"

startup_once ready-check 'startup_step "5/5" "检查全部服务健康状态..."'

for i in $(seq 1 "$WAIT_MAX"); do
  backend_ok=0
  panel_ok=0
  engine_ok=0

  curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1 && backend_ok=1
  curl -fsS "http://127.0.0.1:9000/health" >/dev/null 2>&1 && panel_ok=1
  curl -fsS "http://127.0.0.1/waf-health" >/dev/null 2>&1 && engine_ok=1

  if [ "$backend_ok" = 1 ] && [ "$panel_ok" = 1 ] && [ "$engine_ok" = 1 ]; then
    startup_once brand-banner show_brand_banner
    exit 0
  fi

  if [ "$i" -eq "$WAIT_MAX" ]; then
    startup_warn "部分服务未在 ${WAIT_MAX}s 内就绪（backend=${backend_ok} panel=${panel_ok} engine=${engine_ok}）"
    exit 1
  fi
  sleep 1
done
