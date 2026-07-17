#!/usr/bin/env bash
# 流盾 WAF 版本更新脚本（宝塔 / Docker Compose 环境）
set -euo pipefail

cd "$(dirname "$0")/../.."

echo "==> 流盾 WAF 版本更新"

if [ ! -f .env ]; then
  echo "[错误] 未找到 .env，请先完成首次部署。" >&2
  exit 1
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

if [ -d .git ]; then
  echo "==> 拉取最新代码"
  git pull --ff-only
fi

echo "==> 检查 .env 与 .env.example 差异（请手动合并新增变量）"
diff .env.example .env || true

echo "==> 备份 .env"
cp .env ".env.bak.$(date +%Y%m%d%H%M)"

echo "==> 重建并启动"
$COMPOSE up -d --build

echo "==> 等待健康检查"
sleep 5
$COMPOSE ps

echo "==> 探测服务"
curl -fsS http://127.0.0.1:9000/health >/dev/null && echo "  面板: OK" || echo "  面板: FAIL"
curl -fsS http://127.0.0.1/waf-health >/dev/null && echo "  引擎: OK" || echo "  引擎: FAIL"

echo ""
echo "更新完成。详细说明见 docs/upgrade.md"
