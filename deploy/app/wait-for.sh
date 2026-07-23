#!/usr/bin/env bash
# Wait for Redis (docker compose service name).
set -euo pipefail

source /etc/flowshield/env

# 与 compose app healthcheck start_period 对齐，单独重启 app 时给 Redis 更多恢复时间
WAIT_REDIS_MAX_SEC="${WAIT_REDIS_MAX_SEC:-120}"

echo "[wait-for] waiting for Redis..."
for i in $(seq 1 "$WAIT_REDIS_MAX_SEC"); do
  if [ -n "${REDIS_SOCKET_PATH:-}" ] && [ -S "${REDIS_SOCKET_PATH}" ]; then
    if redis-cli -s "${REDIS_SOCKET_PATH}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
      echo "[wait-for] Redis ready (unix socket)"
      exit 0
    fi
  elif redis-cli -h "${REDIS_HOST}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
    echo "[wait-for] Redis ready (tcp)"
    exit 0
  fi
  if [ "$i" -eq "$WAIT_REDIS_MAX_SEC" ]; then
    echo "[wait-for] Redis timeout after ${WAIT_REDIS_MAX_SEC}s" >&2
    exit 1
  fi
  sleep 1
done
