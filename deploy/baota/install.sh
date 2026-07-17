#!/usr/bin/env bash
# 一键部署脚本（宝塔 / 任意装有 Docker 的 Linux）
set -euo pipefail

# 切到项目根目录（此脚本位于 deploy/baota/）
cd "$(dirname "$0")/../.."

echo "==> 流盾WAF (Flow Shield WAF) 一键部署"

if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 docker，请先在宝塔软件商店安装 Docker 管理器。" >&2
  exit 1
fi

if [ ! -f .env ]; then
  echo "==> 未找到 .env，从 .env.example 生成，请稍后按需修改密码与密钥"
  cp .env.example .env
fi

# 简单校验是否仍使用默认密钥
if grep -q "please_change_this" .env; then
  echo "[警告] .env 中仍有默认密钥（please_change_this...），强烈建议修改后再对外提供服务。"
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

echo "==> 构建并启动容器"
$COMPOSE up -d --build

echo "==> 当前状态"
$COMPOSE ps

PANEL_PORT="$(grep -E '^PANEL_PORT=' .env | cut -d= -f2 || echo 9000)"
echo ""
echo "部署完成！管理面板: http://<服务器IP>:${PANEL_PORT:-9000}"
echo "默认账号见 .env 中 WAF_ADMIN_USER / WAF_ADMIN_PASSWORD"
