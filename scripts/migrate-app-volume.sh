#!/usr/bin/env bash
# 一次性迁移：旧命名卷 waf_sqlite + engine_conf + engine_certs → app_data
# 适用：已部署环境升级到「三卷」布局之前执行。幂等：若 app_data 已有 waf.db 则跳过拷贝。
set -euo pipefail

PROJECT="${COMPOSE_PROJECT_NAME:-flowshield-waf}"
OLD_SQLITE="${PROJECT}_waf_sqlite"
OLD_CONF="${PROJECT}_engine_conf"
OLD_CERTS="${PROJECT}_engine_certs"
NEW_APP="${PROJECT}_app_data"

volume_exists() {
  docker volume inspect "$1" >/dev/null 2>&1
}

echo "==> 卷迁移：${OLD_SQLITE} (+ engine_*) → ${NEW_APP}"

if ! volume_exists "$OLD_SQLITE"; then
  echo "未发现旧卷 ${OLD_SQLITE}，无需迁移（可能已是新布局或全新环境）。"
  exit 0
fi

if volume_exists "$NEW_APP"; then
  has_db="$(docker run --rm -v "${NEW_APP}:/to:ro" alpine \
    sh -c 'test -f /to/waf.db && echo yes || echo no')"
  if [ "$has_db" = "yes" ]; then
    echo "${NEW_APP} 已包含 waf.db，跳过拷贝。"
    exit 0
  fi
  echo "${NEW_APP} 已存在但无 waf.db，将写入数据…"
else
  docker volume create "$NEW_APP" >/dev/null
  echo "已创建 ${NEW_APP}"
fi

echo "==> 停止 compose 服务（避免拷贝过程中写入）…"
if docker compose version >/dev/null 2>&1; then
  docker compose stop || true
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose stop || true
fi

echo "==> 拷贝 SQLite /data …"
docker run --rm \
  -v "${OLD_SQLITE}:/from:ro" \
  -v "${NEW_APP}:/to" \
  alpine sh -c 'cp -a /from/. /to/'

if volume_exists "$OLD_CONF"; then
  echo "==> 覆盖 engine/conf.d …"
  docker run --rm \
    -v "${OLD_CONF}:/from:ro" \
    -v "${NEW_APP}:/to" \
    alpine sh -c 'mkdir -p /to/engine/conf.d && cp -a /from/. /to/engine/conf.d/'
fi

if volume_exists "$OLD_CERTS"; then
  echo "==> 覆盖 engine/certs …"
  docker run --rm \
    -v "${OLD_CERTS}:/from:ro" \
    -v "${NEW_APP}:/to" \
    alpine sh -c 'mkdir -p /to/engine/certs && cp -a /from/. /to/engine/certs/'
fi

echo "==> 校验："
docker run --rm -v "${NEW_APP}:/d:ro" alpine \
  sh -c 'ls -la /d/waf.db /d/engine/conf.d /d/engine/certs 2>/dev/null || ls -la /d'

echo ""
echo "迁移完成。接下来："
echo "  1. docker compose up -d --build"
echo "  2. 确认面板 / 站点 / HTTPS 正常后，可删除旧卷："
echo "     docker volume rm ${OLD_SQLITE} ${OLD_CONF} ${OLD_CERTS} ${PROJECT}_redis_run 2>/dev/null || true"
echo "  3. 若仍有遗留 MySQL 卷且已确认无用："
echo "     docker volume rm ${PROJECT}_mysql_data 2>/dev/null || true"
