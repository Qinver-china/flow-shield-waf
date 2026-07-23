#!/usr/bin/env bash
# Wait until the FastAPI backend is accepting requests (used by engine/panel only).
set -euo pipefail

# shellcheck source=/opt/flowshield/startup-log.sh
source /opt/flowshield/startup-log.sh

WAIT_BACKEND_MAX_SEC="${WAIT_BACKEND_MAX_SEC:-120}"

startup_once backend-wait 'startup_step "4/5" "等待 API 后端就绪..."'
for i in $(seq 1 "$WAIT_BACKEND_MAX_SEC"); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    startup_once backend-ready 'startup_sub "API 后端已就绪 (:8000)"'
    exit 0
  fi
  if [ "$i" -eq "$WAIT_BACKEND_MAX_SEC" ]; then
    startup_warn "API 后端超时 (${WAIT_BACKEND_MAX_SEC}s)，相关服务将降级启动"
    exit 0
  fi
  sleep 1
done
