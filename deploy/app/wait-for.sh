#!/usr/bin/env bash
# Wait for Redis (docker compose service name).
set -euo pipefail

source /etc/flowshield/env

echo "[wait-for] waiting for Redis..."
for i in $(seq 1 60); do
  if [ -n "${REDIS_SOCKET_PATH:-}" ] && [ -S "${REDIS_SOCKET_PATH}" ]; then
    if redis-cli -s "${REDIS_SOCKET_PATH}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
      echo "[wait-for] Redis ready (unix socket)"
      exit 0
    fi
  elif redis-cli -h "${REDIS_HOST}" -a "${REDIS_PASSWORD}" ping 2>/dev/null | grep -q PONG; then
    echo "[wait-for] Redis ready (tcp)"
    exit 0
  fi
  if [ "$i" -eq 60 ]; then
    echo "[wait-for] Redis timeout" >&2
    exit 1
  fi
  sleep 1
done
