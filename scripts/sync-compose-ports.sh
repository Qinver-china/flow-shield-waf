#!/usr/bin/env bash
# 根据 .env 中的 EXTRA_LISTEN_PORTS 生成 docker-compose.override.yml。
# 不要手改该文件；改端口只编辑 .env，再执行本脚本并 docker compose up -d。
# Compose 会自动合并 override.yml，因此不必再写 -f。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
OUT="$ROOT/docker-compose.override.yml"
OLD_EXTRA="$ROOT/docker-compose.extra-ports.yml"

env_val() {
  local key="$1" line val
  [[ -f "$ENV_FILE" ]] || { printf ''; return 0; }
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  [[ -n "$line" ]] || { printf ''; return 0; }
  val="${line#*=}"
  val="${val%$'\r'}"
  val="${val#\"}"
  val="${val%\"}"
  val="${val#\'}"
  val="${val%\'}"
  printf '%s' "$val"
}

is_reserved() {
  local p="$1"
  [[ "$p" == "$http_port" || "$p" == "$https_port" || "$p" == "$panel_port" || "$p" == "80" || "$p" == "443" || "$p" == "9000" ]]
}

panel_port="$(env_val PANEL_PORT)"
panel_port="${panel_port:-9000}"
http_port="$(env_val WAF_HTTP_PORT)"
http_port="${http_port:-80}"
https_port="$(env_val WAF_HTTPS_PORT)"
https_port="${https_port:-443}"
raw="$(env_val EXTRA_LISTEN_PORTS)"
raw_normalized="$(printf '%s' "$raw" | tr ',，;' ' ')"

yaml=""
seen="|"
for p in $raw_normalized; do
  [[ "$p" =~ ^[1-9][0-9]*$ ]] || continue
  if [[ "$p" -gt 65535 ]]; then
    continue
  fi
  if is_reserved "$p"; then
    continue
  fi
  case "$seen" in
    *"|$p|"*) continue ;;
  esac
  seen="${seen}${p}|"
  yaml="${yaml}"$'\n'"      - \"${p}:${p}\""
done

{
  echo "# Auto-generated from EXTRA_LISTEN_PORTS in .env. Do not edit."
  echo "# 改端口请编辑 .env 的 EXTRA_LISTEN_PORTS，然后执行:"
  echo "#   bash scripts/sync-compose-ports.sh && docker compose up -d"
  if [[ -n "$yaml" ]]; then
    echo "services:"
    echo "  app:"
    echo "    ports:$yaml"
  else
    echo "services: {}"
  fi
} >"$OUT"

# 曾短暂写成 extra-ports.yml；迁回 override 以免短命令漏端口。
if [[ -f "$OLD_EXTRA" ]]; then
  rm -f "$OLD_EXTRA"
fi
