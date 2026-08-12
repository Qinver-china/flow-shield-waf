#!/usr/bin/env bash
# 流盾 WAF (Flow Shield WAF) 一键安装 / 更新脚本
#
# 推荐：curl -fsSL https://fswaf.top/install.sh | bash
# 备用：curl -fsSL https://raw.githubusercontent.com/Qinver-china/flow-shield-waf/main/install.sh | bash
#
# 官网：https://fswaf.top
set -euo pipefail

FSWAF_VERSION="1.0.0"
FSWAF_PRODUCT="流盾 WAF"
FSWAF_SLOGAN="守住每一次真实访问"
FSWAF_SITE="https://fswaf.top"
FSWAF_REPO_URL="${FSWAF_REPO_URL:-https://github.com/Qinver-china/flow-shield-waf.git}"
# 国内访问 GitHub 失败/超时时的临时镜像（拉完会恢复官方 origin）
FSWAF_REPO_MIRROR_URL="${FSWAF_REPO_MIRROR_URL:-https://ghproxy.net/https://github.com/Qinver-china/flow-shield-waf.git}"
FSWAF_GIT_TIMEOUT_S="${FSWAF_GIT_TIMEOUT_S:-90}"
FSWAF_REPO_DIR_NAME="flow-shield-waf"
FSWAF_CONTAINER="flowshield-waf-app"
FSWAF_COMPOSE_NAME="flowshield-waf"
FSWAF_META_FILE=".flowshield-install"
FSWAF_DEFAULT_HTTP_ALT=8080
FSWAF_DEFAULT_HTTPS_ALT=4343
FSWAF_DEFAULT_ADMIN_USER="admin"
FSWAF_DEFAULT_ADMIN_PASSWORD="admin888"

# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

c_reset=""
c_bold=""
c_dim=""
c_green=""
c_yellow=""
c_red=""
c_cyan=""
if [[ -t 1 ]]; then
  c_reset=$'\033[0m'
  c_bold=$'\033[1m'
  # 次要文字用浅灰，比 90m 更易读
  c_dim=$'\033[37m'
  c_green=$'\033[32m'
  c_yellow=$'\033[33m'
  c_red=$'\033[31m'
  c_cyan=$'\033[36m'
fi

info() { printf '%s\n' "${c_cyan}==>${c_reset} $*"; }
ok() { printf '%s\n' "${c_green}[OK]${c_reset} $*"; }
warn() { printf '%s\n' "${c_yellow}[警告]${c_reset} $*"; }
err() { printf '%s\n' "${c_red}[错误]${c_reset} $*" >&2; }
die() {
  err "$*"
  exit 1
}

# 长时间无输出时在 /dev/tty 转圈，避免被当成卡死
spin_while() {
  local msg="$1"
  shift
  local pid frames i=0 rc=0
  "$@" &
  pid=$!
  if [[ -t 1 ]] && [[ -w /dev/tty ]]; then
    frames='|/-\'
    while kill -0 "$pid" 2>/dev/null; do
      printf '\r%s %s %c  ' "${c_cyan}==>${c_reset}" "$msg" "${frames:i%4:1}" >/dev/tty
      i=$((i + 1))
      sleep 0.15
    done
    printf '\r%*s\r' 72 '' >/dev/tty
  fi
  wait "$pid" || rc=$?
  return "$rc"
}

# 等待 dockerd 可响应（首次启动常无输出，易被当成卡死）
wait_docker_ready() {
  local timeout_s="${1:-120}"
  local elapsed=0 frames i=0
  frames='|/-\'
  while (( elapsed < timeout_s )); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
      return 0
    fi
    if [[ -t 1 ]] && [[ -w /dev/tty ]]; then
      printf '\r%s 等待 dockerd 就绪（首次启动常需数十秒） %c  %ss/%ss  ' \
        "${c_cyan}==>${c_reset}" "${frames:i%4:1}" "$elapsed" "$timeout_s" >/dev/tty
      i=$((i + 1))
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  if [[ -t 1 ]] && [[ -w /dev/tty ]]; then
    printf '\r%*s\r' 80 '' >/dev/tty
  fi
  return 1
}

# 启用并启动 docker；拆开 enable / start，并提示首次启动为何「看起来卡住」
start_docker_service() {
  command -v systemctl >/dev/null 2>&1 || return 0

  # enable 只建开机软链，通常瞬间完成（你看到的 Created symlink... 就是这一步）
  need_sudo systemctl enable docker >/dev/null 2>&1 || need_sudo systemctl enable docker || true

  if need_sudo systemctl is-active --quiet docker 2>/dev/null; then
    ok "docker 服务已在运行"
    return 0
  fi

  echo
  info "正在启动 dockerd（docker.service）..."
  info "首次启动会初始化 containerd、网桥 docker0、iptables 规则等，终端往往长时间无新输出，属正常。"
  # --no-block：立刻返回，避免 systemctl 静默阻塞；再用轮询显示进度
  if ! need_sudo systemctl start --no-block docker 2>/dev/null; then
    need_sudo systemctl start docker >/dev/null 2>&1 &
  fi
  if wait_docker_ready 180; then
    ok "docker 服务已就绪"
    return 0
  fi
  if need_sudo systemctl is-active --quiet docker 2>/dev/null; then
    ok "docker 服务已启动"
    return 0
  fi
  warn "docker 启动较慢或未就绪，可稍后执行：sudo systemctl status docker"
  return 0
}

# 面板用 ASCII 边框（避免部分 SSH/locale 下 Unicode 框线显示成 ?）
UI_INNER=52

ui_line() {
  local kind="${1:-m}"
  local fill
  fill="$(printf '%*s' "$UI_INNER" '' | tr ' ' '-')"
  case "$kind" in
  t | b) printf '%s+%s+%s\n' "${c_dim}" "$fill" "${c_reset}" ;;
  m) printf '%s+%s+%s\n' "${c_dim}" "$fill" "${c_reset}" ;;
  esac
}

ui_row() {
  # 仅左边界，避免彩色/中文导致右边界对不齐或乱码
  printf '%s|%s %s\n' "${c_dim}" "${c_reset}" "$1"
}

status_mark() {
  local flag="$1"
  if [[ "$flag" -eq 1 ]]; then
    printf '%sOK%s' "${c_green}" "${c_reset}"
  elif [[ "$flag" -eq 2 ]]; then
    printf '%s!!%s' "${c_yellow}" "${c_reset}"
  else
    printf '%sNO%s' "${c_red}" "${c_reset}"
  fi
}

deps_line() {
  printf 'Docker[%s] Compose[%s] Git[%s]' \
    "$(status_mark "$HAVE_DOCKER")" \
    "$(status_mark "$HAVE_COMPOSE")" \
    "$(status_mark "$HAVE_GIT")"
  case "${DOCKER_ACCESS}" in
  sg) printf ' (sg)' ;;
  sudo) printf ' (sudo)' ;;
  esac
  printf '\n'
}

# 安装到当前目录（用户已 cd 到目标路径；不再默认创建子目录）
planned_install_root() {
  pwd
}

dir_is_empty() {
  local dir="${1:-.}"
  [[ -z "$(ls -A "$dir" 2>/dev/null)" ]]
}

# 最初阶段：检测工作目录是否为空（结果进面板；非空立即提示）
check_workdir_empty() {
  if dir_is_empty "."; then
    DIR_EMPTY=1
  else
    DIR_EMPTY=0
  fi
}

default_install_suggest() {
  if [[ -d /www/wwwroot ]]; then
    printf '%s\n' "/www/wwwroot/flow-shield-waf"
  else
    printf '%s\n' "$(pwd)/flow-shield-waf"
  fi
}

# 确保目录存在且当前用户可写。
# 旧逻辑优先 sudo mkdir，装完 Docker 后 sudo 凭证仍有效，会留下 root 属主空目录，
# 随后普通用户 git clone 报：.git: Permission denied
ensure_dir_for_user() {
  local target="$1"
  local me owner
  me="$(id -un)"

  if [[ ! -e "$target" ]]; then
    if mkdir -p "$target" 2>/dev/null; then
      :
    else
      info "当前用户无法直接创建目录，改用 sudo 创建后移交属主..."
      need_sudo mkdir -p "$target" || die "无法创建目录：$target"
      need_sudo chown "$me:" "$target" 2>/dev/null || need_sudo chown "$me" "$target" || die "已创建目录但无法将属主改为 ${me}：$target"
    fi
  elif [[ ! -d "$target" ]]; then
    die "路径已存在但不是目录：$target"
  fi

  if [[ -w "$target" ]]; then
    return 0
  fi

  owner="$(stat -c '%U' "$target" 2>/dev/null || stat -f '%Su' "$target" 2>/dev/null || echo unknown)"
  warn "目录不可写（属主：${owner}）：$target"
  info "尝试用 sudo 将属主改为当前用户 ${me}（常见于上次 sudo 建目录遗留）..."
  need_sudo chown -R "$me:" "$target" 2>/dev/null || need_sudo chown -R "$me" "$target" || die "chown 失败：$target"
  if [[ ! -w "$target" ]]; then
    die "修正属主后仍不可写：$target（请手动：sudo chown -R ${me}: ${target}）"
  fi
  ok "已修正目录属主为：${me}"
}

pick_install_directory() {
  local suggest target
  suggest="$(default_install_suggest)"
  while true; do
    read_tty "请输入安装目录，回车则使用[${suggest}]: " target
    target="${target:-$suggest}"
    ensure_dir_for_user "$target"
    cd "$target" || die "无法进入：$target"
    if dir_is_empty "."; then
      DIR_EMPTY=1
      FORCE_NONEMPTY_INSTALL=0
      ok "已切换到空目录：$(pwd)"
      return 0
    fi
    warn "目标目录仍非空：$(pwd)"
    if confirm "是否在此非空目录强制继续" "N"; then
      DIR_EMPTY=0
      FORCE_NONEMPTY_INSTALL=1
      ok "将强制在此目录继续：$(pwd)"
      return 0
    fi
    suggest="$(pwd)/flow-shield-waf"
  done
}

handle_nonempty_install_dir() {
  # 仅首次安装；已是项目根则跳过
  [[ "$MODE" == "install" ]] || return 0
  is_project_root "." && return 0
  [[ "$DIR_EMPTY" -eq 1 ]] && return 0

  echo
  warn "首次安装：当前目录不是空目录。"
  echo "  git clone 到当前目录通常需要空目录；你可以："
  echo "  1.强制继续（临时克隆后合并到当前目录，同名文件可能被覆盖）"
  echo "  2.重新选择安装目录"
  local choice
  while true; do
    read_tty "请选择 [1/2]: " choice
    case "$choice" in
    1)
      FORCE_NONEMPTY_INSTALL=1
      ok "已选择强制继续"
      return 0
      ;;
    2)
      pick_install_directory
      return 0
      ;;
    *)
      warn "请输入 1 或 2"
      ;;
    esac
  done
}

# curl|bash 时 stdin 是脚本本身，交互必须从 /dev/tty 读，否则会跳过确认或吞掉脚本内容
read_tty() {
  local prompt="$1"
  local __outvar="$2"
  local silent="${3:-0}"
  local __val=""
  if [[ ! -r /dev/tty ]]; then
    die "无法读取终端（/dev/tty）。请改为：curl -fsSL ${FSWAF_SITE}/install.sh -o install.sh && bash install.sh"
  fi
  if [[ "$silent" == "1" ]]; then
    # -s 静默；换行打到终端，避免密码提示粘在同一行
    IFS= read -r -s -p "$prompt" __val </dev/tty || true
    printf '\n' >/dev/tty
  else
    IFS= read -r -p "$prompt" __val </dev/tty || true
  fi
  printf -v "$__outvar" '%s' "$__val"
}

confirm() {
  local prompt="${1:-继续？}"
  local default="${2:-Y}"
  local ans
  if [[ "${FSWAF_ASSUME_YES:-}" == "1" ]]; then
    return 0
  fi
  if [[ "$default" == "Y" ]]; then
    read_tty "$prompt [Y/n] " ans
    [[ -z "$ans" || "$ans" =~ ^[Yy] ]]
  else
    read_tty "$prompt [y/N] " ans
    [[ "$ans" =~ ^[Yy] ]]
  fi
}

# ---------------------------------------------------------------------------
# 系统信息
# ---------------------------------------------------------------------------

OS_FAMILY="unknown" # linux | darwin
OS_ID=""            # ubuntu | debian | centos | rhel | fedora | amzn | ...
OS_VERSION_ID=""    # 如 7 / 9 / 22.04
ARCH="$(uname -m 2>/dev/null || echo unknown)"
HAVE_DOCKER=0
HAVE_COMPOSE=0
HAVE_GIT=0
COMPOSE_CMD=()
# docker 权限通道：direct（当前用户可直连）| sg（本会话用 sg docker）| sudo
DOCKER_ACCESS="none"
MODE="install" # install | update
INSTALL_DIR=""
NGINX_MOVED_HTTP=""
NGINX_MOVED_HTTPS=""
PORT_80_OK=0
PORT_443_OK=0
PORT_9000_OK=0
PORTS_OK=0
PANEL_PORT_CHOSEN=9000
DIR_EMPTY=1
FORCE_NONEMPTY_INSTALL=0

detect_os() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || true)"
  case "$uname_s" in
  Linux*) OS_FAMILY="linux" ;;
  Darwin*) OS_FAMILY="darwin" ;;
  *) OS_FAMILY="unsupported" ;;
  esac
  if [[ "$OS_FAMILY" == "linux" && -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-}"
    OS_VERSION_ID="${VERSION_ID:-}"
  elif [[ "$OS_FAMILY" == "darwin" ]]; then
    OS_ID="macos"
    OS_VERSION_ID=""
  fi
}

need_sudo() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "需要 root 权限执行：$*（请用 root 运行，或安装 sudo）"
  fi
}

rand_secret() {
  local bytes="${1:-32}"
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex "$bytes"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import secrets; print(secrets.token_hex($bytes))"
    return 0
  fi
  # 退化方案
  LC_ALL=C tr -dc 'a-f0-9' </dev/urandom 2>/dev/null | head -c "$((bytes * 2))"
  echo
}

check_arch() {
  case "$ARCH" in
  x86_64 | amd64 | arm64 | aarch64) return 0 ;;
  *)
    warn "当前架构为 $ARCH，未在官方支持列表内（x86_64 / arm64）。可继续，但构建可能失败。"
    ;;
  esac
}

check_resources() {
  local mem_mb=0
  if [[ "$OS_FAMILY" == "linux" ]]; then
    if command -v free >/dev/null 2>&1; then
      mem_mb="$(free -m | awk '/^Mem:/{print $2}')"
    elif [[ -r /proc/meminfo ]]; then
      mem_mb="$(awk '/MemTotal/{printf "%d", $2/1024}' /proc/meminfo)"
    fi
  elif [[ "$OS_FAMILY" == "darwin" ]]; then
    mem_mb="$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%d", $1/1024/1024}')"
  fi
  if [[ -n "$mem_mb" && "$mem_mb" -gt 0 && "$mem_mb" -lt 1800 ]]; then
    warn "检测到内存约 ${mem_mb}MB，建议 ≥ 2GB（含 ClickHouse）。内存过小可能导致构建或运行失败。"
  fi
}

# ---------------------------------------------------------------------------
# 命令检测
# ---------------------------------------------------------------------------

# 刚 usermod -aG docker 后，当前 shell 尚未继承新组；用 sg/sudo 兜底，避免误判「Docker 不可用」
run_docker() {
  case "${DOCKER_ACCESS}" in
  sg)
    # shellcheck disable=SC2048,SC2086
    sg docker -c "docker $(printf '%q ' "$@")"
    ;;
  sudo)
    need_sudo docker "$@"
    ;;
  *)
    docker "$@"
    ;;
  esac
}

run_compose() {
  case "${DOCKER_ACCESS}" in
  sg)
    sg docker -c "$(printf '%q ' "${COMPOSE_CMD[@]}" "$@")"
    ;;
  sudo)
    need_sudo "${COMPOSE_CMD[@]}" "$@"
    ;;
  *)
    "${COMPOSE_CMD[@]}" "$@"
    ;;
  esac
}

probe_docker_access() {
  DOCKER_ACCESS="none"
  if ! command -v docker >/dev/null 2>&1; then
    return 1
  fi
  if docker info >/dev/null 2>&1; then
    DOCKER_ACCESS="direct"
    return 0
  fi
  # 用户已在 docker 组，但当前会话未刷新（一键装机后最常见）
  if command -v sg >/dev/null 2>&1 && sg docker -c 'docker info' >/dev/null 2>&1; then
    DOCKER_ACCESS="sg"
    return 0
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    return 1
  fi
  if command -v sudo >/dev/null 2>&1 && sudo docker info >/dev/null 2>&1; then
    DOCKER_ACCESS="sudo"
    return 0
  fi
  return 1
}

refresh_tool_status() {
  HAVE_DOCKER=0
  HAVE_COMPOSE=0
  HAVE_GIT=0
  COMPOSE_CMD=()
  DOCKER_ACCESS="none"

  if command -v docker >/dev/null 2>&1; then
    if probe_docker_access; then
      HAVE_DOCKER=1
    else
      # 二进制在，但连不上守护进程（或仅差权限且 sg/sudo 也失败）
      HAVE_DOCKER=2
    fi
  fi

  if [[ "$HAVE_DOCKER" -eq 1 ]]; then
    if run_docker compose version >/dev/null 2>&1; then
      HAVE_COMPOSE=1
      COMPOSE_CMD=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
      # 独立 docker-compose 二进制偶发不走 docker socket 权限；仍优先经同一通道试一次
      if [[ "$DOCKER_ACCESS" == "direct" ]] && docker-compose version >/dev/null 2>&1; then
        HAVE_COMPOSE=1
        COMPOSE_CMD=(docker-compose)
      elif [[ "$DOCKER_ACCESS" == "sudo" ]] && need_sudo docker-compose version >/dev/null 2>&1; then
        HAVE_COMPOSE=1
        COMPOSE_CMD=(docker-compose)
      elif [[ "$DOCKER_ACCESS" == "sg" ]] && sg docker -c 'docker-compose version' >/dev/null 2>&1; then
        HAVE_COMPOSE=1
        COMPOSE_CMD=(docker-compose)
      fi
    fi
  fi

  if command -v git >/dev/null 2>&1; then
    HAVE_GIT=1
  fi
}

# 单个紧凑面板：广告词 + 端口 + 检测 + 模式 + 路径
ports_line() {
  printf '80[%s] 443[%s] 面板%d[%s]' \
    "$(status_mark "$PORT_80_OK")" \
    "$(status_mark "$PORT_443_OK")" \
    "${PANEL_PORT_CHOSEN}" \
    "$(status_mark "$PORT_9000_OK")"
  if [[ "$MODE" == "update" ]]; then
    printf '  %s(参考)%s' "${c_dim}" "${c_reset}"
  elif [[ "$PORTS_OK" -eq 1 ]]; then
    printf '  %s通过%s' "${c_green}" "${c_reset}"
  else
    printf '  %s未通过%s' "${c_yellow}" "${c_reset}"
  fi
  printf '\n'
}

print_summary_panel() {
  local mode_label path_label path_value deps ports dir_state
  if [[ "$MODE" == "update" ]]; then
    mode_label="${c_yellow}更新${c_reset}"
    path_label="更新路径"
    path_value="${INSTALL_DIR:-（待指定）}"
  else
    mode_label="${c_green}首次安装${c_reset}"
    path_label="安装路径"
    path_value="$(planned_install_root)"
  fi
  deps="$(deps_line | tr -d '\n')"
  if [[ "$DIR_EMPTY" -eq 1 ]]; then
    dir_state="${c_green}空目录${c_reset}"
  else
    dir_state="${c_yellow}非空${c_reset}"
  fi

  echo
  ui_line t
  ui_row "${c_bold}${FSWAF_PRODUCT}${c_reset}  ${c_dim}${FSWAF_SLOGAN}${c_reset}"
  ui_row "${c_cyan}${FSWAF_SITE}${c_reset}  ${c_dim}v${FSWAF_VERSION}${c_reset}"
  ui_line m
  ui_row "系统  ${OS_FAMILY}/${OS_ID:-?} (${ARCH})"
  if [[ "$MODE" != "update" ]]; then
    ports="$(ports_line | tr -d '\n')"
    ui_row "端口  ${ports}"
  fi
  ui_row "依赖  ${deps}"
  ui_row "模式  ${mode_label}"
  ui_line m
  ui_row "${path_label}  ${c_bold}${path_value}${c_reset}"
  ui_line b
  echo
}

confirm_install_panel() {
  local path_value prompt
  if [[ "$MODE" == "update" && -n "$INSTALL_DIR" ]]; then
    path_value="$INSTALL_DIR"
    prompt="请确认在此路径下更新"
  else
    path_value="$(planned_install_root)"
    prompt="请确认在此路径下安装"
  fi

  print_summary_panel

  # 首次安装 + 非空目录：强制继续 / 重新选择
  handle_nonempty_install_dir
  # 若重选了目录，刷新面板路径展示后再确认
  if [[ "$MODE" != "update" ]]; then
    path_value="$(planned_install_root)"
  fi

  if ! confirm "$prompt" "Y"; then
    echo "已取消。请先 cd 到目标目录后再执行。"
    exit 0
  fi

  # 首次安装且端口未通过：询问是否自动清理（不再二次确认依赖安装）
  if [[ "$MODE" == "install" && "$PORTS_OK" -ne 1 ]]; then
    echo
    warn "存在端口占用，安装前需要处理。"
    if [[ "$PORT_80_OK" -ne 1 ]]; then
      echo "--- :80 ---"
      port_pids 80 || true
    fi
    if [[ "$PORT_443_OK" -ne 1 ]]; then
      echo "--- :443 ---"
      port_pids 443 || true
    fi
    if [[ "$PORT_9000_OK" -ne 1 ]]; then
      echo "--- 面板 9000–9003 均被占用 ---"
      for _p in 9000 9001 9002 9003; do
        echo "  :${_p}"
        port_pids "$_p" || true
      done
    fi
    echo
    if confirm "是否尝试让系统自动清理端口" "Y"; then
      try_auto_free_ports
    else
      err "已取消自动清理。请手动释放 80/443（及面板端口）后重试。"
      echo "  宝塔：把网站监听改为高位端口（如 ${FSWAF_DEFAULT_HTTP_ALT}/${FSWAF_DEFAULT_HTTPS_ALT}）"
      exit 1
    fi
  fi
}

# ---------------------------------------------------------------------------
# 模式判定：安装 / 更新
# ---------------------------------------------------------------------------

is_project_root() {
  local dir="${1:-.}"
  [[ -f "$dir/docker-compose.yml" ]] || return 1
  grep -q "name:[[:space:]]*${FSWAF_COMPOSE_NAME}" "$dir/docker-compose.yml" 2>/dev/null
}

container_exists() {
  command -v docker >/dev/null 2>&1 || return 1
  [[ "$HAVE_DOCKER" -eq 1 ]] || probe_docker_access || return 1
  run_docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$FSWAF_CONTAINER"
}

resolve_install_dir_from_container() {
  local geoip_src project
  geoip_src="$(run_docker inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/nginx/geoip"}}{{.Source}}{{end}}{{end}}' "$FSWAF_CONTAINER" 2>/dev/null || true)"
  if [[ -n "$geoip_src" && -d "$geoip_src" ]]; then
    project="$(cd "$(dirname "$geoip_src")/.." && pwd)"
    if is_project_root "$project"; then
      printf '%s\n' "$project"
      return 0
    fi
  fi
  return 1
}

detect_mode_and_dir() {
  if is_project_root "."; then
    INSTALL_DIR="$(pwd)"
    if container_exists || [[ -f "$INSTALL_DIR/.env" ]]; then
      MODE="update"
    else
      MODE="install"
    fi
    return 0
  fi

  if container_exists; then
    if INSTALL_DIR="$(resolve_install_dir_from_container)"; then
      MODE="update"
      return 0
    fi
    MODE="update"
    INSTALL_DIR=""
    return 0
  fi

  MODE="install"
  INSTALL_DIR=""
}

# ---------------------------------------------------------------------------
# 依赖安装
# ---------------------------------------------------------------------------

install_git_linux() {
  info "安装 Git..."
  case "$OS_ID" in
  ubuntu | debian | linuxmint | pop)
    need_sudo apt-get update -y
    need_sudo apt-get install -y git
    ;;
  centos | rhel | rocky | almalinux | ol | fedora | amzn)
    rpm_install git || die "安装 Git 失败。若为 CentOS 7，请确认已能访问 vault.centos.org，或手动：yum install -y git"
    ;;
  *)
    if command -v apt-get >/dev/null 2>&1; then
      need_sudo apt-get update -y
      need_sudo apt-get install -y git
    elif command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
      rpm_install git || die "安装 Git 失败，请手动安装后重试。"
    else
      die "无法自动安装 Git，请手动安装后重试。"
    fi
    ;;
  esac
  command -v git >/dev/null 2>&1 || die "Git 安装后仍不可用，请检查 PATH。"
  ok "Git 已就绪：$(git --version 2>/dev/null | head -n1)"
}

# CentOS 7 已 EOL：mirrorlist.centos.org 下线后，yum 会长时间卡在「Determining fastest mirrors」
prepare_centos7_yum_repos() {
  [[ "$OS_ID" == "centos" ]] || return 0
  local major="${OS_VERSION_ID%%.*}"
  [[ "$major" == "7" ]] || return 0

  local repos=()
  local f
  shopt -s nullglob
  repos=(/etc/yum.repos.d/CentOS-*.repo /etc/yum.repos.d/CentOS*.repo)
  shopt -u nullglob
  [[ ${#repos[@]} -gt 0 ]] || return 0

  if grep -Rqs 'vault\.centos\.org' "${repos[@]}" 2>/dev/null && \
     ! grep -RqsE '^[[:space:]]*mirrorlist=.*mirrorlist\.centos\.org' "${repos[@]}" 2>/dev/null; then
    return 0
  fi

  if ! grep -RqsE 'mirrorlist\.centos\.org|mirror\.centos\.org' "${repos[@]}" 2>/dev/null; then
    return 0
  fi

  warn "检测到 CentOS 7 仍使用已下线的官方 yum 源，安装 Git/软件时会长时间无响应。"
  info "正在自动切换到 vault.centos.org（归档源，仅保证能装包）..."
  for f in "${repos[@]}"; do
    [[ -f "$f" ]] || continue
    need_sudo cp -a "$f" "${f}.fswaf-bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
    need_sudo sed -i \
      -e 's/^mirrorlist=/#mirrorlist=/g' \
      -e 's/^#[[:space:]]*baseurl=/baseurl=/g' \
      -e 's|mirror\.centos\.org|vault.centos.org|g' \
      "$f"
  done

  if [[ -f /etc/yum/pluginconf.d/fastestmirror.conf ]]; then
    need_sudo sed -i 's/^enabled=1/enabled=0/' /etc/yum/pluginconf.d/fastestmirror.conf 2>/dev/null || true
  fi

  info "清理 yum 缓存并重建（可能需要几十秒）..."
  need_sudo yum clean all >/dev/null 2>&1 || true
  need_sudo yum makecache fast 2>/dev/null || need_sudo yum makecache || warn "yum makecache 未完全成功，将继续尝试安装"
  ok "CentOS 7 yum 源已切换到 vault"
}

# yum/dnf 安装：加超时，避免卡死在选镜像；并先处理 CentOS 7 EOL 源
rpm_install() {
  prepare_centos7_yum_repos
  echo
  info "通过 yum/dnf 安装：$*"
  info "解析/下载软件源时终端可能短暂无新输出，一般 1–3 分钟；若超过 5 分钟仍无进展，请检查网络或镜像源。"
  if command -v dnf >/dev/null 2>&1; then
    need_sudo dnf -y --setopt=timeout=30 --setopt=retries=5 install "$@"
    return $?
  fi
  if command -v yum >/dev/null 2>&1; then
    # 关掉 fastestmirror，避免 CentOS 7 卡在 Determining fastest mirrors
    need_sudo yum -y --setopt=timeout=30 --setopt=retries=5 --disableplugin=fastestmirror install "$@" \
      || need_sudo yum -y --setopt=timeout=30 --setopt=retries=5 install "$@"
    return $?
  fi
  return 1
}

install_git_darwin() {
  info "安装 Git..."
  if command -v brew >/dev/null 2>&1; then
    brew install git
  else
    info "尝试触发 Xcode Command Line Tools 安装（按屏幕提示操作）..."
    xcode-select --install 2>/dev/null || true
    die "请安装 Git 后重新执行本脚本（推荐：xcode-select --install 或安装 Homebrew 后 brew install git）。"
  fi
}

install_docker_linux() {
  info "安装 Docker（含 Compose 插件）..."
  if ! command -v curl >/dev/null 2>&1; then
    case "$OS_ID" in
    ubuntu | debian | linuxmint | pop) need_sudo apt-get update -y && need_sudo apt-get install -y curl ca-certificates ;;
    *)
      if command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1; then
        rpm_install curl ca-certificates || die "需要 curl 才能自动安装 Docker，请先安装 curl。"
      else
        die "需要 curl 才能自动安装 Docker，请先安装 curl。"
      fi
      ;;
    esac
  fi

  local installed=0
  case "$OS_ID" in
  rocky | almalinux | ol)
    # get.docker.com 会加 linux/rocky 源；Rocky 10 该源目前缺 docker-ce 本体，导致 Unable to find a match
    if install_docker_from_rhel_repo; then
      installed=1
    else
      warn "RHEL 兼容源安装失败，再尝试 Docker 官方 get.docker.com ..."
    fi
    ;;
  esac

  if [[ "$installed" -ne 1 ]]; then
    local raw patched
    raw="$(mktemp)"
    patched="$(mktemp)"
    # 官方 get.docker.com 默认 apt -qq 且 >/dev/null，安装包时会长时间无输出
    spin_while "正在下载 Docker 官方安装脚本" curl -fsSL https://get.docker.com -o "$raw"
    # 去掉静默：须整段去掉 2>/dev/null，不能只删 >/dev/null（否则会留下裸数字 2）
    sed -E \
      -e 's/apt_flags="-y -qq"/apt_flags="-y"/g' \
      -e 's/apt-get -y -qq /apt-get -y /g' \
      -e 's/apt-get -qq /apt-get /g' \
      -e 's/dnf -y -q /dnf -y /g' \
      -e 's/dnf -q /dnf /g' \
      -e 's/[[:blank:]]*[0-9]+>\/dev\/null//g' \
      -e 's/[[:blank:]]*>\/dev\/null//g' \
      -e 's/[[:blank:]]*[0-9]+>&[0-9]+//g' \
      "$raw" >"$patched"

    echo
    info "开始安装 Docker 组件（体积较大，可能需要几分钟）..."
    info "若短暂无刷新属正常，并非卡死，请耐心等待。"
    echo
    if need_sudo sh "$patched"; then
      installed=1
    else
      warn "get.docker.com 安装失败"
      case "$OS_ID" in
      rocky | almalinux | ol | rhel | centos)
        info "尝试改用 Docker 官方 RHEL 源回退安装..."
        if install_docker_from_rhel_repo; then
          installed=1
        fi
        ;;
      esac
    fi
    rm -f "$raw" "$patched"
  fi

  [[ "$installed" -eq 1 ]] || die "Docker 安装失败。Rocky/Alma 10 可手动：dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo && dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin"
  command -v docker >/dev/null 2>&1 || die "Docker 包装完后仍找不到 docker 命令"
  echo
  ok "Docker 组件已安装"

  if command -v systemctl >/dev/null 2>&1; then
    start_docker_service
  fi
  if [[ "$(id -u)" -ne 0 ]]; then
    need_sudo usermod -aG docker "$(id -un)" || true
    info "已将当前用户加入 docker 组；本会话将通过 sg docker 继续（无需重登）。"
  fi
}

# Rocky/Alma/OL：官方推荐兼容 RHEL 源。rocky/10 仓库常缺 docker-ce/docker-ce-cli（插件却在），get.docker.com 会装失败。
install_docker_from_rhel_repo() {
  command -v dnf >/dev/null 2>&1 || command -v yum >/dev/null 2>&1 || return 1

  echo
  info "使用 Docker 官方 RHEL 源安装（兼容 Rocky / AlmaLinux / Oracle Linux）..."
  need_sudo rm -f /etc/yum.repos.d/docker-ce.repo /etc/yum.repos.d/docker-ce-staging.repo 2>/dev/null || true

  if command -v dnf >/dev/null 2>&1; then
    need_sudo dnf -y install dnf-plugins-core 2>/dev/null || need_sudo dnf -y install dnf-utils 2>/dev/null || true
    if need_sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null; then
      :
    elif need_sudo yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo 2>/dev/null; then
      :
    else
      # DNF5 部分环境无 config-manager 子命令：直接写入 repo 文件
      need_sudo tee /etc/yum.repos.d/docker-ce.repo >/dev/null <<'EOF'
[docker-ce-stable]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/rhel/$releasever/$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/rhel/gpg
EOF
    fi
    need_sudo dnf -y makecache || true
    # 不强制 rootless/model 插件，避免个别架构缺包导致整次失败
    if ! need_sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
      err "从 RHEL 源安装 docker-ce 失败"
      return 1
    fi
  else
    need_sudo yum -y install yum-utils 2>/dev/null || true
    need_sudo yum-config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo || return 1
    need_sudo yum -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || return 1
  fi

  # Rocky/Alma 10 精简内核常缺 xt_addrtype，Docker 网络会起不来
  local major="${OS_VERSION_ID%%.*}"
  if [[ "$major" == "10" ]] && { [[ "$OS_ID" == "rocky" ]] || [[ "$OS_ID" == "almalinux" ]]; }; then
    info "安装 kernel-modules-extra（EL10 上 Docker 网络常用）..."
    if command -v dnf >/dev/null 2>&1; then
      need_sudo dnf -y install kernel-modules-extra || warn "kernel-modules-extra 安装失败；若 docker 无法建网桥，请手动安装并重启"
    fi
  fi

  ok "已从 RHEL 源安装 Docker"
  return 0
}

ensure_dependencies() {
  refresh_tool_status
  local missing=0

  if [[ "$HAVE_GIT" -ne 1 ]]; then missing=1; fi
  if [[ "$HAVE_DOCKER" -ne 1 ]]; then missing=1; fi
  if [[ "$HAVE_COMPOSE" -ne 1 ]]; then missing=1; fi

  if [[ "$missing" -eq 0 ]]; then
    ok "必备命令已齐全"
    return 0
  fi

  echo
  info "检测到缺失依赖，开始自动安装（Docker / Compose / Git）..."

  if [[ "$HAVE_GIT" -ne 1 ]]; then
    if [[ "$OS_FAMILY" == "linux" ]]; then
      install_git_linux
    else
      install_git_darwin
    fi
  fi

  if [[ "$HAVE_DOCKER" -ne 1 ]]; then
    if [[ "$OS_FAMILY" == "linux" ]]; then
      install_docker_linux
    else
      echo
      err "macOS 需先安装并启动 Docker Desktop："
      echo "  https://docs.docker.com/desktop/setup/install/mac-install/"
      if command -v brew >/dev/null 2>&1; then
        echo "  或：brew install --cask docker  （安装后请打开 Docker.app）"
      fi
      exit 1
    fi
  elif [[ "$HAVE_DOCKER" -eq 2 ]]; then
    if [[ "$OS_FAMILY" == "darwin" ]]; then
      die "检测到 Docker 已安装但未运行，请先打开 Docker Desktop 后再执行。"
    fi
    info "尝试启动 Docker 服务，请稍候..."
    start_docker_service
  fi

  refresh_tool_status

  if [[ "$HAVE_DOCKER" -eq 1 && "$HAVE_COMPOSE" -ne 1 ]]; then
    warn "Docker 可用但未检测到 Compose。Linux 可尝试：sudo apt-get install -y docker-compose-plugin"
    if [[ "$OS_FAMILY" == "linux" ]]; then
      case "$OS_ID" in
      ubuntu | debian | linuxmint | pop)
        need_sudo apt-get update -y || true
        need_sudo apt-get install -y docker-compose-plugin || true
        ;;
      esac
      refresh_tool_status
    fi
  fi

  [[ "$HAVE_GIT" -eq 1 ]] || die "Git 仍不可用"
  [[ "$HAVE_DOCKER" -eq 1 ]] || die "Docker 仍不可用（请确认守护进程已启动；非 root 用户需在 docker 组内）"
  [[ "$HAVE_COMPOSE" -eq 1 ]] || die "Docker Compose 仍不可用"
  case "${DOCKER_ACCESS}" in
  sg) ok "基础环境已就绪（Docker 经 sg docker）" ;;
  sudo) ok "基础环境已就绪（Docker 经 sudo）" ;;
  *) ok "基础环境已就绪" ;;
  esac
}

# ---------------------------------------------------------------------------
# 端口检测与 Nginx 处理
# ---------------------------------------------------------------------------

port_pids() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | awk -v p=":$port" '$4 ~ p"$" || $4 ~ p" "'
    return 0
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
    return 0
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -tlnp 2>/dev/null | grep -E ":${port}[[:space:]]" || true
    return 0
  fi
  return 1
}

port_in_use() {
  local port="$1"
  local out
  out="$(port_pids "$port" 2>/dev/null || true)"
  [[ -n "${out// /}" ]]
}

# 面板端口：9000 起依次尝试 9001/9002/9003；都占用则留给后续交互输入
resolve_panel_port() {
  local p
  PANEL_PORT_CHOSEN=9000
  PORT_9000_OK=0
  for p in 9000 9001 9002 9003; do
    if ! port_in_use "$p"; then
      PANEL_PORT_CHOSEN=$p
      PORT_9000_OK=1
      export FSWAF_PANEL_PORT="$p"
      if [[ "$p" -ne 9000 ]]; then
        info "面板端口 9000 已被占用，自动改用 ${p}"
      fi
      return 0
    fi
  done
  PANEL_PORT_CHOSEN=9000
  PORT_9000_OK=0
  return 1
}

# 仅检测并记录，不弹交互（结果展示在首屏面板）
check_ports_status() {
  PORT_80_OK=0
  PORT_443_OK=0
  PORT_9000_OK=0
  PORTS_OK=0
  PANEL_PORT_CHOSEN=9000
  port_in_use 80 || PORT_80_OK=1
  port_in_use 443 || PORT_443_OK=1
  resolve_panel_port || true
  if [[ "$PORT_80_OK" -eq 1 && "$PORT_443_OK" -eq 1 && "$PORT_9000_OK" -eq 1 ]]; then
    PORTS_OK=1
  fi
}

port_holder_is_nginx() {
  local port="$1"
  local out
  out="$(port_pids "$port" 2>/dev/null || true)"
  echo "$out" | grep -qiE 'nginx|openresty|basename.*/nginx'
}

list_nginx_conf_roots() {
  local roots=()
  local d
  for d in \
    /www/server/panel/vhost/nginx \
    /www/server/nginx/conf \
    /etc/nginx/sites-enabled \
    /etc/nginx/conf.d \
    /etc/nginx \
    /usr/local/etc/nginx \
    /opt/homebrew/etc/nginx; do
    [[ -d "$d" ]] && roots+=("$d")
  done
  # 去重打印
  printf '%s\n' "${roots[@]+"${roots[@]}"}" | awk 'NF && !seen[$0]++'
}

sed_inplace_listen() {
  # 兼容 GNU sed / BSD sed；仅改 listen / listen [::]: 行
  local file="$1"
  local new_http="$2"
  local new_https="$3"
  local tmp out
  tmp="$(mktemp)"
  out="$(mktemp)"
  if ! need_sudo cat "$file" >"$tmp" 2>/dev/null; then
    rm -f "$tmp" "$out"
    return 1
  fi
  if ! sed -E \
    -e "s/(listen[[:space:]]*\[::\]:)80([[:space:];])/\1${new_http}\2/g" \
    -e "s/(listen[[:space:]]*)80([[:space:];])/\1${new_http}\2/g" \
    -e "s/(listen[[:space:]]*\[::\]:)443([[:space:];])/\1${new_https}\2/g" \
    -e "s/(listen[[:space:]]*)443([[:space:];])/\1${new_https}\2/g" \
    "$tmp" >"$out"; then
    rm -f "$tmp" "$out"
    return 1
  fi
  if cmp -s "$tmp" "$out" 2>/dev/null; then
    rm -f "$tmp" "$out"
    return 2
  fi
  if ! need_sudo cp "$out" "$file"; then
    rm -f "$tmp" "$out"
    return 1
  fi
  rm -f "$tmp" "$out"
  return 0
}

backup_and_rewrite_nginx_listen() {
  local new_http="$1"
  local new_https="$2"
  local root backup_root file rel rc
  local changed=0

  backup_root="/tmp/fswaf-nginx-backup-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$backup_root"
  info "备份 Nginx 配置到：${backup_root}"

  while IFS= read -r root; do
    [[ -z "$root" ]] && continue
    while IFS= read -r -d '' file; do
      rel="${file#/}"
      mkdir -p "$backup_root/$(dirname "$rel")"
      need_sudo cp -a "$file" "$backup_root/$rel" 2>/dev/null || cp -a "$file" "$backup_root/$rel" 2>/dev/null || true
      rc=0
      sed_inplace_listen "$file" "$new_http" "$new_https" || rc=$?
      if [[ "$rc" -eq 0 ]]; then
        changed=1
      elif [[ "$rc" -eq 1 ]]; then
        warn "无法自动修改：$file"
      fi
    done < <(find "$root" -type f \( -name '*.conf' -o -name '*.nginx' \) -print0 2>/dev/null)
  done < <(list_nginx_conf_roots)

  if [[ "$changed" -eq 0 ]]; then
    warn "未在常见 Nginx 目录中改写到 listen 80/443（可能配置路径特殊）。备份仍保留：$backup_root"
  else
    ok "已尝试改写 listen 端口：80→${new_http}，443→${new_https}"
  fi

  info "检查并重载 Nginx..."
  if command -v nginx >/dev/null 2>&1; then
    if need_sudo nginx -t; then
      if need_sudo nginx -s reload 2>/dev/null || need_sudo systemctl reload nginx 2>/dev/null || need_sudo service nginx reload 2>/dev/null; then
        ok "Nginx 已重载"
      else
        warn "nginx -t 通过，但 reload 失败，请手动执行：nginx -s reload"
      fi
    else
      die "nginx -t 失败。配置备份在：${backup_root} ，请手动恢复后重试。"
    fi
  else
    warn "未找到 nginx 命令，请在面板中重载 Nginx。"
  fi
}

try_auto_free_ports() {
  local http_port=80 https_port=443 panel_port

  info "尝试自动清理端口..."

  # 面板：若 9000–9003 均占用，才要求用户输入
  if [[ "$PORT_9000_OK" -ne 1 ]]; then
    warn "面板端口 9000 / 9001 / 9002 / 9003 均被占用。"
    while true; do
      read_tty "请输入新的面板端口: " panel_port
      [[ -n "$panel_port" ]] || {
        warn "端口不能为空"
        continue
      }
      [[ "$panel_port" =~ ^[0-9]+$ ]] || {
        warn "请输入数字端口"
        continue
      }
      if port_in_use "$panel_port"; then
        warn "端口 ${panel_port} 仍被占用，请换一个"
        continue
      fi
      PANEL_PORT_CHOSEN=$panel_port
      PORT_9000_OK=1
      export FSWAF_PANEL_PORT="$panel_port"
      ok "面板将使用端口 ${panel_port}"
      break
    done
  fi

  if ! port_in_use "$http_port" && ! port_in_use "$https_port"; then
    PORT_80_OK=1
    PORT_443_OK=1
    if [[ "$PORT_9000_OK" -eq 1 ]]; then
      PORTS_OK=1
    fi
    ok "80/443 已空闲"
    return 0
  fi

  if port_holder_is_nginx "$http_port" || port_holder_is_nginx "$https_port" || command -v nginx >/dev/null 2>&1; then
    info "疑似 Nginx/宝塔占用。将尝试把 Nginx 的 listen 80/443 改到其他端口。"
    local new_http new_https
    read_tty "Nginx 新的 HTTP 端口 [${FSWAF_DEFAULT_HTTP_ALT}]: " new_http
    read_tty "Nginx 新的 HTTPS 端口 [${FSWAF_DEFAULT_HTTPS_ALT}]: " new_https
    new_http="${new_http:-$FSWAF_DEFAULT_HTTP_ALT}"
    new_https="${new_https:-$FSWAF_DEFAULT_HTTPS_ALT}"
    backup_and_rewrite_nginx_listen "$new_http" "$new_https"
    NGINX_MOVED_HTTP="$new_http"
    NGINX_MOVED_HTTPS="$new_https"
    sleep 1
    if port_in_use "$http_port" || port_in_use "$https_port"; then
      echo
      err "调整后 80/443 仍被占用，请手动处理后再执行本脚本："
      port_in_use "$http_port" && port_pids "$http_port" || true
      port_in_use "$https_port" && port_pids "$https_port" || true
      exit 1
    fi
    PORT_80_OK=1
    PORT_443_OK=1
    if [[ "$PORT_9000_OK" -eq 1 ]]; then
      PORTS_OK=1
    fi
    ok "80/443 已释放"
    return 0
  fi

  echo
  err "无法自动清理（占用进程可能不是 Nginx）。请手动处理后重试："
  echo "  - 宝塔：把网站监听改为高位端口（如 ${FSWAF_DEFAULT_HTTP_ALT}/${FSWAF_DEFAULT_HTTPS_ALT}）"
  echo "  - 其它 Web 服务器：修改 listen 或停止服务"
  echo "  - 其它容器：docker ps 查看后 stop/改端口"
  exit 1
}

# ---------------------------------------------------------------------------
# 获取代码 / 生成 .env
# ---------------------------------------------------------------------------

# 带超时执行 git（超时退出码 124）；无 timeout/gtimeout 时用后台轮询兜底
git_cmd_with_timeout() {
  local secs="${FSWAF_GIT_TIMEOUT_S}"
  if command -v timeout >/dev/null 2>&1; then
    timeout "$secs" "$@"
    return $?
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$secs" "$@"
    return $?
  fi
  "$@" &
  local pid=$!
  local elapsed=0
  while kill -0 "$pid" 2>/dev/null; do
    if (( elapsed >= secs )); then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 124
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  wait "$pid"
}

# 官方源失败/超时后，临时改用镜像再试一次；成功后恢复官方 origin
git_clone_with_mirror_fallback() {
  local dest="$1"
  local rc=0

  set +e
  git_cmd_with_timeout git clone --depth 1 "$FSWAF_REPO_URL" "$dest"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    return 0
  fi

  warn "官方源克隆失败或超时（退出码 ${rc}），改用临时镜像重试..."
  if [[ "$dest" == "." ]]; then
    rm -rf .git 2>/dev/null || true
  else
    rm -rf "$dest"
  fi

  set +e
  git_cmd_with_timeout git clone --depth 1 "$FSWAF_REPO_MIRROR_URL" "$dest"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    return "$rc"
  fi

  if [[ "$dest" == "." ]]; then
    git remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true
  else
    git -C "$dest" remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true
  fi
  ok "已通过镜像克隆成功（origin 已恢复为官方地址）"
  return 0
}

git_pull_with_mirror_fallback() {
  local rc=0 orig_url=""

  info "拉取最新代码..."
  set +e
  git_cmd_with_timeout git pull --ff-only origin main
  rc=$?
  if [[ $rc -ne 0 ]]; then
    git_cmd_with_timeout git pull --ff-only
    rc=$?
  fi
  set -e
  if [[ $rc -eq 0 ]]; then
    return 0
  fi

  warn "官方源拉取失败或超时（退出码 ${rc}），改用临时镜像重试..."
  orig_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$orig_url" ]]; then
    warn "无法读取 origin URL，跳过镜像重试"
    warn "git pull 未完全成功，将继续尝试用当前代码构建"
    return 1
  fi
  if [[ "$orig_url" == "$FSWAF_REPO_MIRROR_URL" || "$orig_url" == *ghproxy* ]]; then
    warn "当前 origin 已是镜像地址，git pull 仍失败"
    warn "git pull 未完全成功，将继续尝试用当前代码构建"
    return 1
  fi

  git remote set-url origin "$FSWAF_REPO_MIRROR_URL"
  set +e
  git_cmd_with_timeout git pull --ff-only origin main
  rc=$?
  if [[ $rc -ne 0 ]]; then
    git_cmd_with_timeout git pull --ff-only
    rc=$?
  fi
  set -e
  git remote set-url origin "$orig_url" 2>/dev/null || git remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true

  if [[ $rc -eq 0 ]]; then
    ok "已通过镜像拉取成功（origin 已恢复为官方地址）"
    return 0
  fi
  warn "git pull 未完全成功，将继续尝试用当前代码构建"
  return 1
}

ensure_repo() {
  if [[ -n "$INSTALL_DIR" && -d "$INSTALL_DIR" ]]; then
    cd "$INSTALL_DIR"
    return 0
  fi

  if is_project_root "."; then
    INSTALL_DIR="$(pwd)"
    return 0
  fi

  # 兼容旧版脚本：曾在当前目录下创建 flow-shield-waf/ 子目录
  if [[ -d "$FSWAF_REPO_DIR_NAME" ]] && is_project_root "$FSWAF_REPO_DIR_NAME"; then
    INSTALL_DIR="$(cd "$FSWAF_REPO_DIR_NAME" && pwd)"
    cd "$INSTALL_DIR"
    info "检测到旧版子目录安装，继续使用：$INSTALL_DIR"
    return 0
  fi

  ensure_dir_for_user "$(pwd)"
  info "克隆仓库到当前目录：${FSWAF_REPO_URL}"
  if dir_is_empty "."; then
    git_clone_with_mirror_fallback . || die "git clone 失败（请确认目录可写：$(pwd)）"
  elif [[ "$FORCE_NONEMPTY_INSTALL" -eq 1 ]]; then
    warn "非空目录强制拉取：先克隆到临时目录，再合并到当前目录"
    local tmp
    tmp="$(mktemp -d)"
    git_clone_with_mirror_fallback "$tmp/repo" || die "git clone 失败"
    # 合并：优先保留仓库文件；同名已存在则备份后覆盖
    local f base
    shopt -s dotglob nullglob
    for f in "$tmp/repo"/*; do
      base="$(basename "$f")"
      if [[ -e "./$base" || -L "./$base" ]]; then
        mv "./$base" "./${base}.fswaf-bak.$(date +%Y%m%d%H%M%S)" 2>/dev/null || true
      fi
      mv "$f" .
    done
    shopt -u dotglob nullglob
    rm -rf "$tmp"
  else
    die "当前目录非空且未选择强制继续：$(pwd)"
  fi
  INSTALL_DIR="$(pwd)"
  ok "代码已就绪：$INSTALL_DIR"
}

write_env_file() {
  local gateway="172.17.0.1"
  local panel_port="${FSWAF_PANEL_PORT:-9000}"
  local redis_pw jwt challenge

  if [[ "$OS_FAMILY" == "darwin" ]]; then
    gateway="host.docker.internal"
  fi

  redis_pw="$(rand_secret 16)"
  jwt="$(rand_secret 32)"
  challenge="$(rand_secret 32)"
  FSWAF_ADMIN_USER="${FSWAF_DEFAULT_ADMIN_USER}"
  FSWAF_ADMIN_PASSWORD="${FSWAF_DEFAULT_ADMIN_PASSWORD}"

  cat >.env <<EOF
# Generated by Flow Shield WAF install.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# 官网：${FSWAF_SITE}

DB_PATH=/data/waf.db

REDIS_PASSWORD=${redis_pw}

LOG_LEVEL=WARNING
JWT_SECRET=${jwt}
JWT_ACCESS_TTL_MIN=120
JWT_REFRESH_TTL_DAYS=7
WAF_ADMIN_USER=${FSWAF_ADMIN_USER}
WAF_ADMIN_PASSWORD=${FSWAF_ADMIN_PASSWORD}
WAF_CHALLENGE_SECRET=${challenge}
ENABLE_DOCS=false
CORS_ORIGINS=*
# 默认管理员为 admin / admin888，登录后请立即修改账号密码

PANEL_PORT=${panel_port}

WAF_HTTP_PORT=80
WAF_HTTPS_PORT=443
WAF_ORIGIN_HOST_GATEWAY=${gateway}
EOF

  ok "已生成 .env（服务密钥已随机；管理员使用默认账号）"
}

merge_missing_env_from_example() {
  [[ -f .env.example ]] || return 0
  [[ -f .env ]] || return 0
  local key val
  # 仅补齐 .env 中缺失的 KEY（不覆盖已有值）
  while IFS= read -r line; do
    [[ "$line" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] || continue
    key="${line%%=*}"
    if grep -qE "^${key}=" .env; then
      continue
    fi
    val="${line#*=}"
    echo "${key}=${val}" >>.env
    info "已向 .env 追加新变量：${key}"
  done <.env.example
}

write_meta() {
  cat >"$FSWAF_META_FILE" <<EOF
installed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
install_dir=$(pwd)
script_version=${FSWAF_VERSION}
os=${OS_FAMILY}/${OS_ID}
EOF
}

# ---------------------------------------------------------------------------
# 构建启动 / 健康检查
# ---------------------------------------------------------------------------

compose() {
  run_compose "$@"
}

build_and_start() {
  info "拉取依赖镜像并本地构建启动（首次安装可能较久，约10-20分钟）..."
  compose up -d --build
  ok "容器已启动"
}

wait_healthy() {
  local panel_port i
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"

  info "等待健康检查（最长约 3 分钟）..."
  for i in $(seq 1 36); do
    if curl -fsS "http://127.0.0.1:${panel_port}/health" >/dev/null 2>&1 &&
      curl -fsS "http://127.0.0.1/waf-health" >/dev/null 2>&1; then
      ok "面板与引擎健康检查通过"
      return 0
    fi
    sleep 5
  done
  warn "健康检查超时，请查看：docker compose -f $(pwd)/docker-compose.yml ps / logs"
  compose ps || true
  return 0
}

print_success() {
  local kind="${1:-install}" # install | update
  local title panel_port host_hint admin_user admin_pass panel_url
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"
  admin_user="$(grep -E '^WAF_ADMIN_USER=' .env 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
  admin_pass="$(grep -E '^WAF_ADMIN_PASSWORD=' .env 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)"
  admin_user="${admin_user:-$FSWAF_DEFAULT_ADMIN_USER}"
  admin_pass="${admin_pass:-$FSWAF_DEFAULT_ADMIN_PASSWORD}"
  host_hint="<服务器IP>"
  if [[ "$OS_FAMILY" == "darwin" ]]; then
    host_hint="127.0.0.1"
  fi
  panel_url="http://${host_hint}:${panel_port}"
  if [[ "$kind" == "update" ]]; then
    title="更新完成"
  else
    title="部署完成"
  fi

  echo
  ui_line t
  ui_row "${c_bold}${c_green}${title}${c_reset}  ${c_dim}${FSWAF_PRODUCT}${c_reset}"
  ui_line m
  ui_row "目录  $(pwd)"
  ui_row "面板  ${panel_url}"
  if [[ "$kind" == "install" ]]; then
    ui_row "账号  ${admin_user}"
    ui_row "密码  ${admin_pass}"
  else
    ui_row "文档  ${FSWAF_SITE}/guide/upgrade-backup"
  fi
  ui_line m
  ui_row "${c_bold}${FSWAF_PRODUCT}${c_reset} ${c_dim}${FSWAF_SLOGAN}${c_reset}"
  ui_line b

  if [[ "$kind" == "install" ]]; then
    ui_row "${c_bold}${c_red}进入面板后请务必先修改管理员账号和管理员密码${c_reset}"
  fi

  if [[ "$kind" == "install" && -n "$NGINX_MOVED_HTTP" ]]; then
    echo
    info "Nginx 已改为 HTTP ${NGINX_MOVED_HTTP} / HTTPS ${NGINX_MOVED_HTTPS}，回源请填新端口"
  fi
  if [[ "$kind" == "install" ]]; then
    echo
    info "文档：${FSWAF_SITE}/guide/first-site"
  fi
  echo
}

# ---------------------------------------------------------------------------
# 更新流程
# ---------------------------------------------------------------------------

run_update() {
  if [[ -z "$INSTALL_DIR" ]]; then
    echo
    warn "检测到已有 ${FSWAF_CONTAINER} 容器，但未能自动定位项目目录。"
    read_tty "请输入流盾项目根目录路径: " INSTALL_DIR
    [[ -n "$INSTALL_DIR" ]] || die "未提供目录"
  fi
  cd "$INSTALL_DIR" || die "无法进入：$INSTALL_DIR"
  is_project_root "." || die "目录不像流盾项目根（缺少 docker-compose.yml / name: ${FSWAF_COMPOSE_NAME}）：$(pwd)"

  [[ -f .env ]] || die "未找到 .env，无法更新。若需重装请先处理旧容器后重新安装。"

  info "更新模式：$(pwd)"
  cp .env ".env.bak.$(date +%Y%m%d%H%M%S)"
  ok "已备份 .env"

  if [[ -d .git ]]; then
    git_pull_with_mirror_fallback || true
  else
    warn "当前目录不是 git 仓库，跳过 pull（若用压缩包部署请自行覆盖代码并保留 .env）"
  fi

  merge_missing_env_from_example
  build_and_start
  wait_healthy
  write_meta
  print_success update
}

# ---------------------------------------------------------------------------
# 首次安装流程
# ---------------------------------------------------------------------------

run_install() {
  ensure_repo
  if [[ -f .env ]]; then
    warn "目录中已存在 .env，将保留并直接启动（不覆盖密钥）。"
    if ! confirm "继续使用现有 .env 启动？" "Y"; then
      die "已取消。如需重新生成，请先备份并删除 .env 后再执行。"
    fi
  else
    write_env_file
  fi
  write_meta
  build_and_start
  wait_healthy
  print_success install
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

main() {
  detect_os

  if [[ "$OS_FAMILY" == "unsupported" ]]; then
    die "当前系统不受支持。请在 Linux 服务器、宝塔环境或 macOS（Docker Desktop）上执行。"
  fi

  check_arch
  check_resources
  refresh_tool_status
  detect_mode_and_dir
  check_workdir_empty
  if [[ "$MODE" != "update" ]]; then
    check_ports_status
  fi
  confirm_install_panel

  ensure_dependencies

  # 依赖装好后重新判定一次（例如刚装好 docker 才能看到容器）
  detect_mode_and_dir

  if [[ "$MODE" == "update" ]]; then
    run_update
  else
    run_install
  fi
}

main "$@"
