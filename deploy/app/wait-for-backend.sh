#!/usr/bin/env bash
# Wait until the FastAPI backend is accepting requests (used by engine/panel only).
set -euo pipefail

echo "[wait-for] waiting for backend /health..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    echo "[wait-for] backend ready"
    exit 0
  fi
  if [ "$i" -eq 60 ]; then
    echo "[wait-for] backend timeout — starting engine anyway (WAF will use Redis config or pass-through)" >&2
    exit 0
  fi
  sleep 1
done
