#!/usr/bin/env bash
# 流盾 WAF：MySQL → SQLite + ClickHouse 流水 一键迁移（0.3.0+）
#
# 适用：线上仍为旧版四容器（含 mysql），已拉取含本脚本的新代码。
#
# 用法：
#   bash scripts/migrate-to-sqlite.sh           # 交互确认
#   bash scripts/migrate-to-sqlite.sh -y        # 跳过确认
#   bash scripts/migrate-to-sqlite.sh --migrate-only   # 仅迁移，不重启栈
#   bash scripts/migrate-to-sqlite.sh --skip-backup    # 跳过备份（不推荐）
#   bash scripts/migrate-to-sqlite.sh --no-flow-import # 不导入 AI/预警/流量异常历史
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-flowshield-waf}"
NETWORK_NAME="${COMPOSE_PROJECT_NAME}_waf_net"
SQLITE_VOLUME="${COMPOSE_PROJECT_NAME}_waf_sqlite"
APP_IMAGE="${APP_IMAGE:-flowshield-waf-app:latest}"

AUTO_YES=0
MIGRATE_ONLY=0
SKIP_BACKUP=0
IMPORT_FLOW=1
FLOW_ONLY=0
DO_PULL=0

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  echo ""
  echo "选项："
  echo "  -y, --yes              跳过交互确认"
  echo "  --migrate-only         只执行备份+迁移，不 down/up 服务"
  echo "  --skip-backup          跳过 MySQL / .env 备份"
  echo "  --no-flow-import       不将 MySQL 流水表导入 ClickHouse"
  echo "  --flow-only            仅补跑流水导入（SQLite 已迁移时使用）"
  echo "  --pull                 迁移前 git pull --ff-only origin main"
  echo "  -h, --help             显示帮助"
}

log()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[警告]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes) AUTO_YES=1; shift ;;
    --migrate-only) MIGRATE_ONLY=1; shift ;;
    --skip-backup) SKIP_BACKUP=1; shift ;;
    --no-flow-import) IMPORT_FLOW=0; shift ;;
    --flow-only) FLOW_ONLY=1; IMPORT_FLOW=1; shift ;;
    --pull) DO_PULL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "未知参数: $1（使用 -h 查看帮助）" ;;
  esac
done

if [[ ! -f .env ]]; then
  die "未找到 .env，请先在项目根目录完成首次部署。"
fi

if [[ ! -f scripts/migrate_mysql_to_sqlite.py ]]; then
  die "未找到 scripts/migrate_mysql_to_sqlite.py，请先 git pull 到 0.3.0+ 代码。"
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

# 加载 .env（供备份与 URL 拼接；compose 仍会自行读取 .env）
set -a
# shellcheck disable=SC1091
source .env
set +a

MYSQL_USER="${MYSQL_USER:-waf}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-waf}"
DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-}"
CLICKHOUSE_DATABASE="${CLICKHOUSE_DATABASE:-waf}"

if [[ -z "$MYSQL_PASSWORD" ]]; then
  die "MYSQL_PASSWORD 为空，请检查 .env。"
fi

find_mysql_container() {
  local c=""
  if $COMPOSE config --services 2>/dev/null | grep -qx mysql; then
    c="$($COMPOSE ps -q mysql 2>/dev/null | head -1 || true)"
    if [[ -n "$c" ]]; then
        docker ps -a --filter "id=$c" --format '{{.Names}}'
        return 0
    fi
  fi
  c="$(docker ps -a \
    --filter "label=com.docker.compose.project=${COMPOSE_PROJECT_NAME}" \
    --format '{{.Names}}' 2>/dev/null | grep -i mysql | head -1 || true)"
  if [[ -n "$c" ]]; then
    echo "$c"
    return 0
  fi
  c="$(docker ps -a --format '{{.Names}}' | grep -iE '(flowshield.*mysql|mysql.*flowshield|waf.*mysql)' | head -1 || true)"
  [[ -n "$c" ]] && echo "$c"
}

ensure_mysql_running() {
  local name="$1"
  if docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null | grep -qx true; then
    return 0
  fi
  log "启动 MySQL 容器: $name"
  docker start "$name" >/dev/null
  local i
  for i in $(seq 1 30); do
    if docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" "$name" \
      mysqladmin ping -h127.0.0.1 -u"$MYSQL_USER" --silent 2>/dev/null; then
      return 0
    fi
    sleep 2
  done
  die "MySQL 容器 $name 启动后仍无法 ping 通，请检查日志: docker logs $name"
}

connect_mysql_network() {
  local name="$1"
  if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    return 0
  fi
  if docker network inspect "$NETWORK_NAME" --format '{{range .Containers}}{{.Name}} {{end}}' | grep -qE "(^| )${name}( |$)"; then
    return 0
  fi
  log "将 MySQL 接入网络 $NETWORK_NAME"
  docker network connect "$NETWORK_NAME" "$name" 2>/dev/null || true
}

confirm() {
  [[ "$AUTO_YES" -eq 1 ]] && return 0
  echo ""
  warn "即将：备份 → MySQL 迁 SQLite →（可选）流水入 ClickHouse → 停旧栈 → 启动新栈（无 mysql）"
  read -r -p "是否继续？[y/N] " ans
  [[ "${ans:-}" =~ ^[Yy]$ ]] || die "已取消。"
}

BACKUP_DIR=""
do_backup() {
  if [[ "$SKIP_BACKUP" -eq 1 ]]; then
    warn "已跳过备份（--skip-backup）"
    BACKUP_DIR="(已跳过)"
    return 0
  fi

  BACKUP_DIR="$ROOT/backup/migrate_$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  log "备份目录: $BACKUP_DIR"

  cp .env "$BACKUP_DIR/.env"
  $COMPOSE ps >"$BACKUP_DIR/compose_ps.txt" 2>&1 || true

  log "导出 MySQL: $BACKUP_DIR/mysql.sql"
  docker exec -e MYSQL_PWD="$MYSQL_PASSWORD" -i "$MYSQL_CONTAINER" \
    mysqldump -u"$MYSQL_USER" --single-transaction --no-tablespaces --routines --triggers \
    "$MYSQL_DATABASE" >"$BACKUP_DIR/mysql.sql"

  if [[ -s "$BACKUP_DIR/mysql.sql" ]]; then
    log "MySQL 备份完成 ($(wc -c <"$BACKUP_DIR/mysql.sql" | tr -d ' ') bytes)"
  else
    die "MySQL 备份文件为空，已中止。"
  fi
}

run_migration() {
  log "创建 SQLite 数据卷（若不存在）: $SQLITE_VOLUME"
  docker volume create "$SQLITE_VOLUME" >/dev/null

  log "构建 app 镜像（迁移需完整 Python 依赖）..."
  $COMPOSE build app

  log "执行数据迁移（配置 → SQLite，流水 → ClickHouse）..."
  local migrate_args=(
    /work/scripts/migrate_mysql_to_sqlite.py
    --sqlite-path /data/waf.db
    --clickhouse-host clickhouse
    --clickhouse-port 8123
    --clickhouse-user "$CLICKHOUSE_USER"
    --clickhouse-password "$CLICKHOUSE_PASSWORD"
    --clickhouse-database "$CLICKHOUSE_DATABASE"
  )
  [[ "$IMPORT_FLOW" -eq 1 ]] && migrate_args+=(--import-clickhouse-flow)
  [[ "$FLOW_ONLY" -eq 1 ]] && migrate_args+=(--flow-only)

  docker run --rm \
    --entrypoint /opt/venv/bin/python \
    --network "$NETWORK_NAME" \
    -v "$SQLITE_VOLUME:/data" \
    -v "$ROOT:/work:ro" \
    --env-file .env \
    -e DB_PATH=/data/waf.db \
    -e DB_HOST=mysql \
    -e CLICKHOUSE_HOST=clickhouse \
    -e PYTHONPATH=/app/backend \
    "$APP_IMAGE" \
    "${migrate_args[@]}"

  docker run --rm -v "$SQLITE_VOLUME:/data" alpine ls -lh /data/waf.db \
    || { [[ "$FLOW_ONLY" -eq 1 ]] || die "未找到 /data/waf.db，迁移可能失败。"; }
}

restart_stack() {
  log "停止当前 Compose 栈（保留数据卷，不加 -v）..."
  $COMPOSE down --remove-orphans

  log "启动新架构（redis + clickhouse + app）..."
  $COMPOSE up -d --build

  log "等待服务就绪..."
  local i
  for i in $(seq 1 36); do
    if curl -fsS "http://127.0.0.1:${PANEL_PORT:-9000}/health" >/dev/null 2>&1 \
      && curl -fsS http://127.0.0.1/waf-health >/dev/null 2>&1; then
      break
    fi
    sleep 5
  done
  $COMPOSE ps

  local ok=1
  if curl -fsS "http://127.0.0.1:${PANEL_PORT:-9000}/health" >/dev/null 2>&1; then
    log "面板健康检查: OK"
  else
    warn "面板健康检查: FAIL（可执行: $COMPOSE logs --tail=80 app）"
    ok=0
  fi
  if curl -fsS http://127.0.0.1/waf-health >/dev/null 2>&1; then
    log "引擎健康检查: OK"
  else
    warn "引擎健康检查: FAIL"
    ok=0
  fi

  [[ "$ok" -eq 1 ]] || warn "部分健康检查未通过，请查看日志。"
}

# ---- main ----
log "流盾 WAF MySQL → SQLite 一键迁移"

if [[ "$DO_PULL" -eq 1 ]]; then
  if [[ -d .git ]]; then
    log "拉取最新代码..."
    git pull --ff-only origin main
  else
    warn "非 git 目录，跳过 --pull"
  fi
fi

confirm

log "确保 redis / clickhouse 运行..."
$COMPOSE up -d redis clickhouse

log "等待 redis / clickhouse 健康..."
$COMPOSE up -d --wait redis clickhouse 2>/dev/null || {
  for _ in $(seq 1 30); do
    $COMPOSE ps redis clickhouse 2>/dev/null | grep -q healthy && break
    sleep 2
  done
}

if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  die "Docker 网络 $NETWORK_NAME 不存在，请检查 compose 项目名。"
fi

MYSQL_CONTAINER="$(find_mysql_container || true)"
if [[ -z "$MYSQL_CONTAINER" ]]; then
  die "未找到 MySQL 容器。请确认旧版 mysql 仍在（docker ps -a | grep mysql），或先恢复 mysql 后再迁移。"
fi
log "MySQL 容器: $MYSQL_CONTAINER"

ensure_mysql_running "$MYSQL_CONTAINER"
connect_mysql_network "$MYSQL_CONTAINER"

do_backup
run_migration

if [[ "$MIGRATE_ONLY" -eq 1 ]]; then
  log "仅迁移模式完成。SQLite 已写入卷 $SQLITE_VOLUME。"
  log "确认无误后手动执行: $COMPOSE down && $COMPOSE up -d --build"
  exit 0
fi

restart_stack

echo ""
log "迁移完成。"
echo "  备份: ${BACKUP_DIR:-无}"
echo "  SQLite 卷: $SQLITE_VOLUME"
echo "  面板: http://127.0.0.1:${PANEL_PORT:-9000}"
echo ""
warn "稳定运行数天后，可手动清理旧 MySQL 容器与卷："
echo "  docker rm -f $MYSQL_CONTAINER"
echo "  docker volume rm ${COMPOSE_PROJECT_NAME}_mysql_data   # 不可恢复，务必确认备份齐全"
