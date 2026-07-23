#!/usr/bin/env bash
# Wait for Redis (docker compose service name).
set -euo pipefail

source /etc/flowshield/env
# shellcheck source=/opt/flowshield/startup-log.sh
source /opt/flowshield/startup-log.sh

# 与 compose app healthcheck start_period 对齐，单独重启 app 时给 Redis 更多恢复时间
WAIT_REDIS_MAX_SEC="${WAIT_REDIS_MAX_SEC:-120}"

startup_once redis-wait 'startup_step "2/5" "等待 Redis 连接..."'
for i in $(seq 1 "$WAIT_REDIS_MAX_SEC"); do
  if [ -n "${REDIS_SOCKET_PATH:-}" ] && [ -S "${REDIS_SOCKET_PATH}" ]; then
    if redis-cli -s "${REDIS_SOCKET_PATH}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
      startup_once redis-ready 'startup_sub "Redis 已就绪 (unix socket)"'
      exit 0
    fi
  elif redis-cli -h "${REDIS_HOST}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
    startup_once redis-ready 'startup_sub "Redis 已就绪 (tcp)"'
    exit 0
  fi
  if [ "$i" -eq "$WAIT_REDIS_MAX_SEC" ]; then
    startup_warn "Redis 连接超时 (${WAIT_REDIS_MAX_SEC}s)"
    exit 1
  fi
  sleep 1
done
