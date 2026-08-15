#!/usr/bin/env bash
# Wait until the FastAPI backend is accepting requests (used by engine/panel only).
set -euo pipefail

# shellcheck source=/opt/flowshield/startup-log.sh
source /opt/flowshield/startup-log.sh

WAIT_BACKEND_MAX_SEC="${WAIT_BACKEND_MAX_SEC:-120}"

# uvicorn 以 root 创建 socket（约 755），Nginx/OpenResty worker 需要能 connect。
relax_backend_sock() {
  if [ -S /run/flowshield/backend.sock ]; then
    chmod 666 /run/flowshield/backend.sock || true
  fi
}

startup_once backend-wait 'startup_step "4/5" "等待 API 后端就绪..."'
for i in $(seq 1 "$WAIT_BACKEND_MAX_SEC"); do
  if curl -fsS --unix-socket /run/flowshield/backend.sock http://localhost/health >/dev/null 2>&1; then
    relax_backend_sock
    startup_once backend-ready 'startup_sub "API 后端已就绪 (unix socket)"'
    exit 0
  fi
  if [ "$i" -eq "$WAIT_BACKEND_MAX_SEC" ]; then
    relax_backend_sock
    startup_warn "API 后端超时 (${WAIT_BACKEND_MAX_SEC}s)，相关服务将降级启动"
    exit 0
  fi
  sleep 1
done
