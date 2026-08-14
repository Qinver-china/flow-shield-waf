#!/usr/bin/env bash
# 全新启动：删除所有 Docker 卷并重新构建、拉起服务
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 停止并删除容器与数据卷..."
docker compose down -v --remove-orphans

echo "==> 重新构建 app 镜像..."
docker compose build app

echo "==> 启动全部服务..."
docker compose up -d

echo "==> 等待健康检查..."
docker compose ps

echo ""
echo "全新环境已就绪。面板: http://localhost:${PANEL_PORT:-9000}"
