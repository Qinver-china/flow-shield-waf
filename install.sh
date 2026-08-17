#!/usr/bin/env bash
# 流盾 WAF (Flow Shield WAF) 一键安装 / 更新脚本
#
# 推荐：curl -fsSL https://fswaf.top/install.sh | bash
# 备用：curl -fsSL https://raw.githubusercontent.com/Qinver-china/flow-shield-waf/main/install.sh | bash
#
# 官网：https://fswaf.top
set -euo pipefail

FSWAF_VERSION="1.0.5"
FSWAF_PRODUCT="流盾 WAF"
FSWAF_SLOGAN="守住每一次真实访问"
FSWAF_SITE="https://fswaf.top"
FSWAF_REPO_URL="${FSWAF_REPO_URL:-https://github.com/Qinver-china/flow-shield-waf.git}"
# 国内访问 GitHub 失败/超时时按顺序尝试的临时镜像（拉完会恢复官方 origin）。
# 可用 FSWAF_REPO_MIRROR_URLS 覆盖整表（空格分隔）；FSWAF_REPO_MIRROR_URL 会插到最前（兼容旧用法）。
FSWAF_GIT_TIMEOUT_S="${FSWAF_GIT_TIMEOUT_S:-600}"
FSWAF_GIT_PROBE_TIMEOUT_S="${FSWAF_GIT_PROBE_TIMEOUT_S:-30}"
_FSWAF_DEFAULT_MIRRORS=(
  "https://ghproxy.net/https://github.com/Qinver-china/flow-shield-waf.git"
  "https://gh-proxy.com/https://github.com/Qinver-china/flow-shield-waf.git"
  "https://gitclone.com/github.com/Qinver-china/flow-shield-waf.git"
  "https://gh.llkk.cc/https://github.com/Qinver-china/flow-shield-waf.git"
)
if [[ -n "${FSWAF_REPO_MIRROR_URLS:-}" ]]; then
  # shellcheck disable=SC2206
  FSWAF_REPO_MIRROR_LIST=(${FSWAF_REPO_MIRROR_URLS})
else
  FSWAF_REPO_MIRROR_LIST=("${_FSWAF_DEFAULT_MIRRORS[@]}")
  if [[ -n "${FSWAF_REPO_MIRROR_URL:-}" ]]; then
    FSWAF_REPO_MIRROR_LIST=("${FSWAF_REPO_MIRROR_URL}" "${FSWAF_REPO_MIRROR_LIST[@]}")
  fi
fi
# 兼容旧逻辑里对单一镜像变量的读取
FSWAF_REPO_MIRROR_URL="${FSWAF_REPO_MIRROR_URL:-${FSWAF_REPO_MIRROR_LIST[0]}}"
FSWAF_REPO_DIR_NAME="flow-shield-waf"
FSWAF_CONTAINER="flowshield-waf-app"
FSWAF_COMPOSE_NAME="flowshield-waf"
FSWAF_META_FILE=".flowshield-install"
FSWAF_DEFAULT_HTTP_ALT=8080
FSWAF_DEFAULT_HTTPS_ALT=4343

# 国内加速（安装确认后交互选择）：Docker Hub / apk / pip / npm / Git 优先走国内源
FSWAF_CN_MIRROR="${FSWAF_CN_MIRROR:-0}"
_FSWAF_CN_DOCKER_MIRRORS=(
  "https://docker.1ms.run"
  "https://docker.1panel.live"
  "https://docker.xuanyuan.me"
)
FSWAF_CN_PIP_INDEX_URL="${FSWAF_CN_PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
FSWAF_CN_PIP_TRUSTED_HOST="${FSWAF_CN_PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"
FSWAF_CN_ALPINE_MIRROR="${FSWAF_CN_ALPINE_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/alpine}"
FSWAF_CN_NPM_REGISTRY="${FSWAF_CN_NPM_REGISTRY:-https://registry.npmmirror.com}"
# 清华等常见镜像站没有 nginx.org/download 目录，默认仍走官网；填了无效地址会 404
FSWAF_CN_NGINX_MIRROR="${FSWAF_CN_NGINX_MIRROR:-}"
FSWAF_CN_CARGO_REGISTRY="${FSWAF_CN_CARGO_REGISTRY:-sparse+https://mirrors.tuna.tsinghua.edu.cn/crates.io-index/}"
# 可由 FSWAF_CN_DOCKER_MIRRORS 覆盖整表（空格分隔）
if [[ -n "${FSWAF_CN_DOCKER_MIRRORS:-}" ]]; then
  # shellcheck disable=SC2206
  _FSWAF_CN_DOCKER_MIRROR_LIST=(${FSWAF_CN_DOCKER_MIRRORS})
else
  _FSWAF_CN_DOCKER_MIRROR_LIST=("${_FSWAF_CN_DOCKER_MIRRORS[@]}")
fi

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
      detect_mode_and_dir
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

_compose_passthrough_env_args() {
  COMPOSE_PASSTHROUGH_ENV=()
  [[ -n "${FSWAF_PIP_INDEX_URL:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_PIP_INDEX_URL=${FSWAF_PIP_INDEX_URL}" )
  [[ -n "${FSWAF_PIP_TRUSTED_HOST:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_PIP_TRUSTED_HOST=${FSWAF_PIP_TRUSTED_HOST}" )
  [[ -n "${FSWAF_ALPINE_MIRROR:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_ALPINE_MIRROR=${FSWAF_ALPINE_MIRROR}" )
  [[ -n "${FSWAF_NPM_REGISTRY:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_NPM_REGISTRY=${FSWAF_NPM_REGISTRY}" )
  [[ -n "${FSWAF_NGINX_MIRROR:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_NGINX_MIRROR=${FSWAF_NGINX_MIRROR}" )
  [[ -n "${FSWAF_CARGO_REGISTRY:-}" ]] && COMPOSE_PASSTHROUGH_ENV+=( "FSWAF_CARGO_REGISTRY=${FSWAF_CARGO_REGISTRY}" )
}

run_compose() {
  local sg_cmd env_prefix="" arg
  _compose_passthrough_env_args
  case "${DOCKER_ACCESS}" in
  sg)
    sg_cmd="$(printf '%q ' "${COMPOSE_CMD[@]}" "$@")"
    if ((${#COMPOSE_PASSTHROUGH_ENV[@]} > 0)); then
      env_prefix=""
      local key val
      for arg in "${COMPOSE_PASSTHROUGH_ENV[@]}"; do
        key="${arg%%=*}"
        val="${arg#*=}"
        env_prefix+=" ${key}=${val@Q}"
      done
      sg docker -c "${env_prefix# } ${sg_cmd}"
    else
      sg docker -c "$sg_cmd"
    fi
    ;;
  sudo)
    if ((${#COMPOSE_PASSTHROUGH_ENV[@]} > 0)); then
      need_sudo env "${COMPOSE_PASSTHROUGH_ENV[@]}" "${COMPOSE_CMD[@]}" "$@"
    else
      need_sudo "${COMPOSE_CMD[@]}" "$@"
    fi
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
  # 若重选了目录，刷新模式与路径后再确认
  if [[ "$MODE" == "update" && -n "$INSTALL_DIR" ]]; then
    path_value="$INSTALL_DIR"
    prompt="请确认在此路径下更新"
  else
    path_value="$(planned_install_root)"
    prompt="请确认在此路径下安装"
  fi

  if ! confirm "$prompt" "Y"; then
    echo "已取消。请先 cd 到目标目录后再执行。"
    exit 0
  fi

  prompt_cn_mirror_choice

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

# 路径确认且模式判定完成后询问（仅当次构建/拉取生效，不写入 .env）
prompt_cn_mirror_choice() {
  local ans

  if [[ "${FSWAF_CN_MIRROR_ASKED:-}" == "1" ]]; then
    return 0
  fi
  FSWAF_CN_MIRROR_ASKED=1

  if [[ "${FSWAF_ASSUME_YES:-}" == "1" ]]; then
    if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
      export FSWAF_CN_MIRROR=1
      ok "国内加速：是（由 FSWAF_CN_MIRROR=1 指定）"
    else
      FSWAF_CN_MIRROR=0
      ok "国内加速：否（非交互模式默认海外直连）"
    fi
    return 0
  fi

  while true; do
    read_tty "是否启用国内镜像源加速？国内服务器请输入 Y，海外服务器请输入 N： " ans
    case "$ans" in
    Y | y)
      FSWAF_CN_MIRROR=1
      export FSWAF_CN_MIRROR=1
      ok "已启用国内加速"
      return 0
      ;;
    N | n)
      FSWAF_CN_MIRROR=0
      ok "已选择海外直连（未启用国内加速）"
      return 0
      ;;
    "")
      warn "请输入 Y 或 N"
      ;;
    *)
      warn "请输入 Y 或 N"
      ;;
    esac
  done
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

# 带超时执行命令（超时退出码 124）；无 timeout/gtimeout 时用后台轮询兜底
_git_cmd_with_secs() {
  local secs="$1"
  shift
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

git_cmd_with_timeout() {
  _git_cmd_with_secs "${FSWAF_GIT_TIMEOUT_S}" "$@"
}

git_mirror_host() {
  printf '%s\n' "$1" | sed -E 's#https://([^/]+)/.*#\1#'
}

git_restore_official_origin() {
  local dest="${1:-}"
  if [[ "$dest" == "." || -z "$dest" ]]; then
    git remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true
  else
    git -C "$dest" remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true
  fi
}

git_clean_clone_dest() {
  local dest="$1"
  if [[ "$dest" == "." ]]; then
    rm -rf .git 2>/dev/null || true
  else
    rm -rf "$dest"
  fi
}

# 短超时探测 git 智能 HTTP 是否可达，避免死镜像拖满克隆超时
git_probe_url() {
  local url="$1"
  GIT_TERMINAL_PROMPT=0 _git_cmd_with_secs "${FSWAF_GIT_PROBE_TIMEOUT_S}" \
    git ls-remote --heads "$url" >/dev/null 2>&1
}

# 官方源失败/超时后，按顺序尝试国内镜像；成功后恢复官方 origin
git_clone_mirrors_first() {
  local dest="$1"
  local rc=0 mirror="" host=""

  info "国内加速：优先从 Git 镜像克隆..."
  for mirror in "${FSWAF_REPO_MIRROR_LIST[@]}"; do
    host="$(git_mirror_host "$mirror")"
    info "探测镜像：${host}"
    if ! git_probe_url "$mirror"; then
      warn "镜像不可达，跳过：${host}"
      continue
    fi
    git_clean_clone_dest "$dest"
    info "克隆镜像：${host}"
    set +e
    git_cmd_with_timeout git clone --depth 1 "$mirror" "$dest"
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
      git_restore_official_origin "$dest"
      ok "已通过镜像 ${host} 克隆成功（origin 已恢复为官方地址）"
      return 0
    fi
    warn "镜像克隆失败（退出码 ${rc}）：${host}"
  done

  warn "国内 Git 镜像均未成功，尝试官方 GitHub..."
  git_clean_clone_dest "$dest"
  set +e
  git_cmd_with_timeout git clone --depth 1 "$FSWAF_REPO_URL" "$dest"
  rc=$?
  set -e
  [[ $rc -eq 0 ]] || return "$rc"
  return 0
}

git_clone_with_mirror_fallback() {
  local dest="$1"
  local rc=0 mirror="" host=""

  if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
    git_clone_mirrors_first "$dest"
    return $?
  fi

  set +e
  git_cmd_with_timeout git clone --depth 1 "$FSWAF_REPO_URL" "$dest"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    return 0
  fi

  warn "官方源克隆失败或超时（退出码 ${rc}），将依次尝试国内镜像..."
  for mirror in "${FSWAF_REPO_MIRROR_LIST[@]}"; do
    host="$(git_mirror_host "$mirror")"
    info "探测镜像：${host}"
    if ! git_probe_url "$mirror"; then
      warn "镜像不可达，跳过：${host}"
      continue
    fi
    git_clean_clone_dest "$dest"
    info "克隆镜像：${host}"
    set +e
    git_cmd_with_timeout git clone --depth 1 "$mirror" "$dest"
    rc=$?
    set -e
    if [[ $rc -eq 0 ]]; then
      git_restore_official_origin "$dest"
      ok "已通过镜像 ${host} 克隆成功（origin 已恢复为官方地址）"
      return 0
    fi
    warn "镜像克隆失败（退出码 ${rc}）：${host}"
  done
  return "$rc"
}

git_force_sync_main() {
  # fetch 后强制对齐 origin/main：覆盖已跟踪文件的本地改动；.env 等 ignore/未跟踪文件保留
  local rc=0
  set +e
  git_cmd_with_timeout git fetch --depth 1 origin main
  rc=$?
  set -e
  [[ $rc -eq 0 ]] || return "$rc"
  git checkout -f main >/dev/null 2>&1 || git checkout -B main origin/main >/dev/null 2>&1 || true
  git reset --hard origin/main
}

git_pull_with_mirror_fallback() {
  local rc=0 orig_url="" dirty=""

  info "拉取最新代码..."
  dirty="$(git status --porcelain --untracked-files=no 2>/dev/null || true)"
  if [[ -n "$dirty" ]]; then
    warn "检测到本地代码有改动，一键更新将强制覆盖为远程 main（保留 .env 等未被 git 跟踪的文件）"
  fi

  if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
    info "国内加速：优先从 Git 镜像拉取..."
    orig_url="$(git remote get-url origin 2>/dev/null || true)"
    if [[ -n "$orig_url" ]]; then
      for mirror in "${FSWAF_REPO_MIRROR_LIST[@]}"; do
        [[ "$mirror" == "$orig_url" ]] && continue
        host="$(git_mirror_host "$mirror")"
        info "探测镜像：${host}"
        if ! git_probe_url "$mirror"; then
          warn "镜像不可达，跳过：${host}"
          continue
        fi
        info "拉取镜像：${host}"
        git remote set-url origin "$mirror"
        set +e
        git_force_sync_main
        rc=$?
        set -e
        git remote set-url origin "$orig_url" 2>/dev/null || git_restore_official_origin "." || true
        if [[ $rc -eq 0 ]]; then
          ok "已通过镜像 ${host} 拉取成功（origin 已恢复为官方地址）"
          return 0
        fi
        warn "镜像拉取失败（退出码 ${rc}）：${host}"
      done
      warn "国内 Git 镜像均未成功，尝试官方 GitHub..."
    fi
  fi

  set +e
  git_force_sync_main
  rc=$?
  set -e
  if [[ $rc -eq 0 ]]; then
    ok "代码已更新到最新"
    return 0
  fi

  warn "官方源拉取失败或超时（退出码 ${rc}），将依次尝试国内镜像..."
  orig_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$orig_url" ]]; then
    warn "无法读取 origin URL，跳过镜像重试"
    warn "git 拉取未完全成功，将继续尝试用当前代码构建"
    return 1
  fi

  local mirror="" host=""
  for mirror in "${FSWAF_REPO_MIRROR_LIST[@]}"; do
    [[ "$mirror" == "$orig_url" ]] && continue
    host="$(git_mirror_host "$mirror")"
    info "探测镜像：${host}"
    if ! git_probe_url "$mirror"; then
      warn "镜像不可达，跳过：${host}"
      continue
    fi
    info "拉取镜像：${host}"
    git remote set-url origin "$mirror"
    set +e
    git_force_sync_main
    rc=$?
    set -e
    git remote set-url origin "$orig_url" 2>/dev/null || git remote set-url origin "$FSWAF_REPO_URL" 2>/dev/null || true
    if [[ $rc -eq 0 ]]; then
      ok "已通过镜像 ${host} 拉取成功（origin 已恢复为官方地址）"
      return 0
    fi
    warn "镜像拉取失败（退出码 ${rc}）：${host}"
  done
  warn "git 拉取未完全成功，将继续尝试用当前代码构建"
  return 1
}

# 无 .git 时下载最新代码覆盖项目文件；保留 .env，Docker 数据卷不在目录内故不受影响
overlay_project_from_fresh_clone() {
  local tmp dest f base
  tmp="$(mktemp -d)"
  dest="$tmp/repo"
  info "正在下载最新代码..."
  if ! git_clone_with_mirror_fallback "$dest"; then
    rm -rf "$tmp"
    warn "下载最新代码失败，将继续使用当前目录代码构建"
    return 1
  fi
  shopt -s dotglob nullglob
  for f in "$dest"/*; do
    base="$(basename "$f")"
    case "$base" in
    . | .. | .env) continue ;;
    esac
    rm -rf "./${base}"
    mv "$f" "./${base}"
  done
  shopt -u dotglob nullglob
  rm -rf "$tmp"
  ok "已用最新代码覆盖项目文件（.env 与 Docker 数据卷未改动）"
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
    git_clone_with_mirror_fallback . || die "git clone 失败"
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

  cat >.env <<EOF
# Generated by Flow Shield WAF install.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)
# 官网：${FSWAF_SITE}

DB_PATH=/data/waf.db

REDIS_PASSWORD=${redis_pw}

LOG_LEVEL=WARNING
JWT_SECRET=${jwt}
JWT_ACCESS_TTL_MIN=120
# 登录会话有效期（天）
JWT_REFRESH_TTL_DAYS=3
WAF_CHALLENGE_SECRET=${challenge}
ENABLE_DOCS=false
CORS_ORIGINS=*
# 首次打开面板时设置管理员账号密码

PANEL_PORT=${panel_port}

WAF_HTTP_PORT=80
WAF_HTTPS_PORT=443
# 站点自定义额外监听的访问端口，例如：888,8443
# 不要手改 docker-compose.override.yml，只改本变量后执行：
# bash scripts/sync-compose-ports.sh && docker compose up -d
EXTRA_LISTEN_PORTS=
WAF_ORIGIN_HOST_GATEWAY=${gateway}
EOF

  ok "已生成 .env（服务密钥已随机）"
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

# 旧默认 7 天改为 3 天；已自定义的其它值不改
sync_jwt_refresh_ttl() {
  [[ -f .env ]] || return 0
  grep -qE '^JWT_REFRESH_TTL_DAYS=7$' .env || return 0
  if sed --version >/dev/null 2>&1; then
    sed -i 's/^JWT_REFRESH_TTL_DAYS=7$/JWT_REFRESH_TTL_DAYS=3/' .env
  else
    sed -i '' 's/^JWT_REFRESH_TTL_DAYS=7$/JWT_REFRESH_TTL_DAYS=3/' .env
  fi
  info "已将登录有效期从 7 天调整为 3 天（JWT_REFRESH_TTL_DAYS）"
}

# 从 .env 移除构建期国内镜像变量（避免 Compose 自动读取 .env 后长期生效）
clear_cn_mirror_env_file() {
  local key file=".env"
  [[ -f "$file" ]] || return 0
  for key in FSWAF_PIP_INDEX_URL FSWAF_PIP_TRUSTED_HOST FSWAF_ALPINE_MIRROR FSWAF_NPM_REGISTRY FSWAF_NGINX_MIRROR FSWAF_CARGO_REGISTRY; do
    if sed --version >/dev/null 2>&1; then
      sed -i "/^${key}=/d" "$file"
    else
      sed -i '' "/^${key}=/d" "$file"
    fi
  done
  if sed --version >/dev/null 2>&1; then
    sed -i '/^# 国内加速（install\.sh --cn）$/d' "$file"
  else
    sed -i '' '/^# 国内加速（install\.sh --cn）$/d' "$file"
  fi
}

unset_cn_build_env() {
  unset FSWAF_PIP_INDEX_URL FSWAF_PIP_TRUSTED_HOST FSWAF_ALPINE_MIRROR FSWAF_NPM_REGISTRY \
    FSWAF_NGINX_MIRROR FSWAF_CARGO_REGISTRY
}

# 构建前按是否启用国内加速设置或清除镜像环境变量；不写入 .env
prepare_build_mirror_env() {
  if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
    export_cn_build_env
    return 0
  fi
  unset_cn_build_env
  clear_cn_mirror_env_file
}

export_cn_build_env() {
  export FSWAF_PIP_INDEX_URL="${FSWAF_CN_PIP_INDEX_URL}"
  export FSWAF_PIP_TRUSTED_HOST="${FSWAF_CN_PIP_TRUSTED_HOST}"
  export FSWAF_ALPINE_MIRROR="${FSWAF_CN_ALPINE_MIRROR}"
  export FSWAF_NPM_REGISTRY="${FSWAF_CN_NPM_REGISTRY}"
  export FSWAF_NGINX_MIRROR="${FSWAF_CN_NGINX_MIRROR}"
  export FSWAF_CARGO_REGISTRY="${FSWAF_CN_CARGO_REGISTRY}"
}

write_meta() {
  local cn_line=""
  if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
    cn_line=$'\n'"cn_mirror=1"
  fi
  cat >"$FSWAF_META_FILE" <<EOF
installed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
install_dir=$(pwd)
script_version=${FSWAF_VERSION}
os=${OS_FAMILY}/${OS_ID}${cn_line}
EOF
}

# ---------------------------------------------------------------------------
# Docker Hub 镜像加速（registry-mirrors）兼容
# ---------------------------------------------------------------------------

# 2024-06 起多数高校/厂商公开 Docker Hub 缓存已停服或仅校内可用；
# 若 daemon.json 仍指向它们，pull 会报 lookup ... no such host / 403。
_FSWAF_DEAD_DOCKER_MIRROR_HOSTS=(
  docker.mirrors.ustc.edu.cn
  hub-mirror.c.163.com
  mirror.baidubce.com
  docker.mirrors.sjtug.sjtu.edu.cn
  docker.nju.edu.cn
  registry.docker-cn.com
  dockerhub.azk8s.cn
  mirror.ccs.tencentyun.com
)

is_known_dead_docker_mirror_host() {
  local host="$1" h
  for h in "${_FSWAF_DEAD_DOCKER_MIRROR_HOSTS[@]}"; do
    [[ "$host" == "$h" ]] && return 0
  done
  return 1
}

docker_mirror_host_from_url() {
  local url="$1"
  url="${url#https://}"
  url="${url#http://}"
  url="${url%%/*}"
  url="${url%%:*}"
  printf '%s\n' "$url"
}

# 列出当前生效的 Registry Mirrors（来自 dockerd）
list_docker_registry_mirrors() {
  run_docker info 2>/dev/null | awk '
    /^ Registry Mirrors:/ { flag=1; next }
    flag && /^[[:space:]]+https?:\/\// { gsub(/^[[:space:]]+/, ""); print; next }
    flag { exit }
  '
}

docker_mirror_host_resolvable() {
  local host="$1"
  [[ -n "$host" ]] || return 1
  if command -v getent >/dev/null 2>&1; then
    getent ahosts "$host" >/dev/null 2>&1 && return 0
    getent hosts "$host" >/dev/null 2>&1 && return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import socket,sys; socket.getaddrinfo(sys.argv[1],443)" "$host" >/dev/null 2>&1 && return 0
  fi
  # 无解析工具时不误判为不可达
  return 0
}

# 从 /etc/docker/daemon.json 去掉指定镜像 URL（保留其它配置）；成功返回 0
strip_docker_registry_mirrors_from_daemon_json() {
  local daemon_json="/etc/docker/daemon.json"
  local tmp bak raw
  [[ -f "$daemon_json" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1

  tmp="$(mktemp)"
  bak="${daemon_json}.bak.flowshield.$(date +%Y%m%d%H%M%S)"
  # "$@" = 要移除的完整 mirror URL 列表；用 sudo cat 读配置，避免 sudo+heredoc 吞 stdin
  raw="$(need_sudo cat "$daemon_json")" || {
    rm -f "$tmp"
    return 1
  }
  if ! printf '%s\n' "$raw" | python3 -c '
import json, sys

def norm_url(u):
    return (u or "").strip().rstrip("/")

def host(u):
    u = norm_url(u)
    for p in ("https://", "http://"):
        if u.lower().startswith(p):
            u = u[len(p):]
            break
    return u.split("/")[0].split(":")[0].lower()

remove = [x for x in sys.argv[1:] if x]
remove_urls = {norm_url(x) for x in remove}
remove_hosts = {host(x) for x in remove}
data = json.load(sys.stdin)
mirrors = data.get("registry-mirrors") or []
if not isinstance(mirrors, list):
    mirrors = []
kept = [
    m for m in mirrors
    if norm_url(m) not in remove_urls and host(m) not in remove_hosts
]
if kept:
    data["registry-mirrors"] = kept
else:
    data.pop("registry-mirrors", None)
json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")
' "$@" >"$tmp"; then
    rm -f "$tmp"
    return 1
  fi

  need_sudo cp "$daemon_json" "$bak" || {
    rm -f "$tmp"
    return 1
  }
  # install 保证 /etc 下文件属主为 root，避免 mv 把用户属主带进 /etc
  if ! need_sudo install -m 644 "$tmp" "$daemon_json"; then
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
  info "已备份原配置：$bak"
  return 0
}

# 向 daemon.json 合并 registry-mirrors（不重复）；成功返回 0
merge_docker_registry_mirrors_to_daemon_json() {
  local daemon_json="/etc/docker/daemon.json"
  local tmp bak raw
  [[ -f "$daemon_json" ]] || return 1
  command -v python3 >/dev/null 2>&1 || return 1

  tmp="$(mktemp)"
  bak="${daemon_json}.bak.flowshield.$(date +%Y%m%d%H%M%S)"
  raw="$(need_sudo cat "$daemon_json")" || {
    rm -f "$tmp"
    return 1
  }
  if ! printf '%s\n' "$raw" | python3 -c '
import json, sys

def norm_url(u):
    return (u or "").strip().rstrip("/")

def host(u):
    u = norm_url(u)
    for p in ("https://", "http://"):
        if u.lower().startswith(p):
            u = u[len(p):]
            break
    return u.split("/")[0].split(":")[0].lower()

args = [x for x in sys.argv[1:] if x]
dead_hosts = set()
add = args
if "--" in args:
    i = args.index("--")
    add = args[:i]
    dead_hosts = {x.lower() for x in args[i + 1:]}
data = json.load(sys.stdin)
mirrors = data.get("registry-mirrors") or []
if not isinstance(mirrors, list):
    mirrors = []
kept = []
seen = set()
for m in mirrors:
    if host(m) in dead_hosts:
        continue
    key = norm_url(m)
    if key in seen:
        continue
    seen.add(key)
    kept.append(m)
for m in add:
    if host(m) in dead_hosts:
        continue
    key = norm_url(m)
    if not m or key in seen:
        continue
    kept.insert(0, m)
    seen.add(key)
if kept:
    data["registry-mirrors"] = kept
else:
    data.pop("registry-mirrors", None)
json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")
' "$@" -- "${_FSWAF_DEAD_DOCKER_MIRROR_HOSTS[@]}" >"$tmp"; then
    rm -f "$tmp"
    return 1
  fi

  need_sudo cp "$daemon_json" "$bak" || {
    rm -f "$tmp"
    return 1
  }
  if ! need_sudo install -m 644 "$tmp" "$daemon_json"; then
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
  info "已备份原配置：$bak"
  return 0
}

create_docker_daemon_json_with_mirrors() {
  local daemon_json="/etc/docker/daemon.json"
  local tmp
  command -v python3 >/dev/null 2>&1 || return 1
  tmp="$(mktemp)"
  if ! python3 -c '
import json, sys
json.dump({"registry-mirrors": sys.argv[1:]}, sys.stdout, ensure_ascii=False, indent=2)
sys.stdout.write("\n")
' "$@" >"$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  need_sudo mkdir -p /etc/docker
  if ! need_sudo install -m 644 "$tmp" "$daemon_json"; then
    rm -f "$tmp"
    return 1
  fi
  rm -f "$tmp"
  return 0
}

apply_china_docker_registry_mirrors() {
  local reachable=() m host
  local daemon_json="/etc/docker/daemon.json"

  [[ "$HAVE_DOCKER" -eq 1 ]] || probe_docker_access || return 0

  if [[ "$OS_FAMILY" != "linux" ]]; then
    warn "非 Linux：请在本机 Docker 引擎配置 registry-mirrors（Docker Desktop → Docker Engine）："
    for m in "${_FSWAF_CN_DOCKER_MIRROR_LIST[@]}"; do
      echo "  - $m"
    done
    return 0
  fi

  for m in "${_FSWAF_CN_DOCKER_MIRROR_LIST[@]}"; do
    host="$(docker_mirror_host_from_url "$m")"
    if is_known_dead_docker_mirror_host "$host"; then
      continue
    fi
    if docker_mirror_host_resolvable "$host"; then
      reachable+=("$m")
    else
      warn "Docker 镜像加速源不可达，跳过：${host}"
    fi
  done

  if ((${#reachable[@]} == 0)); then
    warn "未探测到可用的 Docker Hub 国内镜像，镜像拉取将使用当前 Docker 配置或直连"
    return 0
  fi

  info "配置 Docker Hub 国内镜像加速..."
  if [[ -f "$daemon_json" ]]; then
    if merge_docker_registry_mirrors_to_daemon_json "${reachable[@]}"; then
      info "正在重启 Docker 使镜像加速生效..."
      if reload_docker_after_daemon_json; then
        ok "已添加 Docker Hub 镜像加速"
      else
        warn "daemon.json 已更新，但 Docker 重启失败，请手动：sudo systemctl restart docker"
      fi
    else
      warn "自动写入 daemon.json 失败，请手动添加 registry-mirrors 后重启 Docker"
    fi
  else
    if create_docker_daemon_json_with_mirrors "${reachable[@]}"; then
      info "正在重启 Docker 使镜像加速生效..."
      if reload_docker_after_daemon_json; then
        ok "已创建 daemon.json 并启用 Docker Hub 镜像加速"
      else
        warn "daemon.json 已创建，但 Docker 重启失败，请手动：sudo systemctl restart docker"
      fi
    else
      warn "无法创建 /etc/docker/daemon.json，请手动配置 registry-mirrors"
    fi
  fi
}

apply_china_mirror_settings() {
  info "国内加速已启用：Docker Hub / apk / pip / npm / Git 将优先使用国内镜像"
  export_cn_build_env
  apply_china_docker_registry_mirrors || true
}

reload_docker_after_daemon_json() {
  if command -v systemctl >/dev/null 2>&1; then
    need_sudo systemctl restart docker || return 1
    wait_docker_ready 120 || true
    return 0
  fi
  need_sudo service docker restart 2>/dev/null || return 1
  wait_docker_ready 120 || true
  return 0
}

# 检测失效 registry-mirrors；Linux 上可自动剔除并重启 dockerd
sanitize_docker_registry_mirrors() {
  local mirrors=()
  local bad=()
  local m host
  local line

  [[ "${_FSWAF_SANITIZE_DONE:-0}" == "1" ]] && return 0
  [[ "$HAVE_DOCKER" -eq 1 ]] || probe_docker_access || return 0

  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    mirrors+=("$line")
  done < <(list_docker_registry_mirrors)

  ((${#mirrors[@]})) || return 0

  for m in "${mirrors[@]}"; do
    host="$(docker_mirror_host_from_url "$m")"
    if is_known_dead_docker_mirror_host "$host"; then
      bad+=("$m")
      continue
    fi
    if ! docker_mirror_host_resolvable "$host"; then
      bad+=("$m")
    fi
  done

  ((${#bad[@]})) || {
    _FSWAF_SANITIZE_DONE=1
    return 0
  }

  _FSWAF_SANITIZE_DONE=1
  echo
  warn "检测到 Docker 配置了不可用的镜像加速源（registry-mirrors）："
  for m in "${bad[@]}"; do
    echo "  - $m"
  done
  warn "常见于已下线的中科大/网易等源；继续拉取会报 lookup ... no such host。"

  if [[ "$OS_FAMILY" != "linux" ]]; then
    warn "请在 Docker Desktop → Settings → Docker Engine 中删除上述地址后 Apply & Restart。"
    return 0
  fi

  if [[ ! -f /etc/docker/daemon.json ]]; then
    warn "未找到 /etc/docker/daemon.json，请手动清理 registry-mirrors 后执行：sudo systemctl restart docker"
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    warn "系统无 python3，无法自动改写 daemon.json。请手动删除上述镜像源后：sudo systemctl restart docker"
    return 0
  fi

  if ! confirm "是否自动从 daemon.json 移除失效镜像源并重启 Docker？" "Y"; then
    warn "已跳过自动修复。若稍后 pull 失败，请手动编辑 /etc/docker/daemon.json"
    return 0
  fi

  if strip_docker_registry_mirrors_from_daemon_json "${bad[@]}"; then
    info "正在重启 Docker 使配置生效..."
    if reload_docker_after_daemon_json; then
      ok "已移除失效镜像加速源"
    else
      warn "daemon.json 已更新，但 Docker 重启失败，请手动：sudo systemctl restart docker"
    fi
  else
    warn "自动改写 daemon.json 失败，请手动删除失效 registry-mirrors 后重启 Docker"
  fi
}

print_docker_pull_hint() {
  echo
  err "依赖镜像拉取/构建失败。建议更换Docker可用的加速源后，再重新执行安装命令(文档：${FSWAF_SITE}/guide/faq-deploy)"
}

# ---------------------------------------------------------------------------
# 构建启动 / 健康检查
# ---------------------------------------------------------------------------

compose() {
  if [[ -f ./scripts/sync-compose-ports.sh ]]; then
    bash ./scripts/sync-compose-ports.sh || true
  fi
  run_compose "$@"
}

build_and_start() {
  sanitize_docker_registry_mirrors || true
  prepare_build_mirror_env
  info "拉取依赖镜像并本地构建启动（首次安装可能较久，约10-20分钟）..."
  if ! compose up -d --build; then
    print_docker_pull_hint
    die "docker compose up 失败"
  fi
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

# ---------------------------------------------------------------------------
# 本机宝塔 / 1Panel：健康检查后写入 same_server 账号（失败不阻断安装）
# ---------------------------------------------------------------------------

_read_trim_file() {
  local f="$1"
  [[ -f "$f" ]] || return 1
  tr -d '\r' <"$f" | head -n 1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

_host_python() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
  elif command -v python >/dev/null 2>&1; then
    python "$@"
  else
    return 1
  fi
}

_write_local_panel_account() {
  local provider="$1" name="$2" panel_url="$3" api_key="${4:-}" extra="${5:-}" remark="${6:-}"
  local out
  if ! out="$(
    run_docker exec \
      -e "PANEL_PROVIDER=${provider}" \
      -e "PANEL_NAME=${name}" \
      -e "PANEL_URL=${panel_url}" \
      -e "PANEL_API_KEY=${api_key}" \
      -e "PANEL_SAME_SERVER=1" \
      -e "PANEL_VERIFY_TLS=0" \
      -e "PANEL_EXTRA=${extra}" \
      -e "PANEL_REMARK=${remark}" \
      "$FSWAF_CONTAINER" \
      /opt/venv/bin/python -m app.cli.bootstrap_local_panel
  )"; then
    warn "写入「${name}」失败：${out}"
    return 1
  fi
  if echo "$out" | grep -q '^skipped '; then
    info "已存在同服务器 ${provider} 账号，跳过覆盖"
  else
    ok "已写入面板账号：${name}"
  fi
  if echo "$out" | grep -q 'missing_api_key'; then
    warn "「${name}」未检测到 API 密钥。请在 1Panel 开启 API 接口后，到流盾「系统设置 → 面板集成」补全密钥"
  fi
  return 0
}

# 探测本机用于对外通信的 IPv4（排除回环与链路本地）。失败返回非 0。
_detect_host_ipv4() {
  local ip="" iface

  if command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit }}' || true)"
  fi

  if [[ -z "$ip" ]]; then
    ip="$(_host_python -c 'import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(2);s.connect(("1.1.1.1",80));print(s.getsockname()[0]);s.close()' 2>/dev/null || true)"
    ip="$(printf '%s' "$ip" | tr -d '\r' | awk 'NF{line=$0} END{print line}')"
  fi

  if [[ -z "$ip" && "${OS_FAMILY:-}" != "darwin" ]] && command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^([0-9]{1,3}\.){3}[0-9]{1,3}$/ && $i !~ /^127\./ && $i !~ /^169\.254\./ && $i != "0.0.0.0") {
          print $i; exit
        }
      }
    }' || true)"
  fi

  if [[ -z "$ip" && "${OS_FAMILY:-}" == "darwin" ]]; then
    for iface in en0 en1; do
      ip="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
      [[ -n "$ip" ]] && break
    done
  fi

  ip="$(printf '%s' "$ip" | tr -d '\r' | awk 'NF{print $1; exit}')"
  [[ "$ip" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]] || return 1
  case "$ip" in
  127.* | 0.0.0.0 | 169.254.*) return 1 ;;
  esac
  printf '%s\n' "$ip"
}

# 宝塔 API 白名单看到的是容器源 IP，不是固定的 docker0 网关 172.17.0.1。
# 收集：本机公网/局域网 IP、本机回环、app 容器 IP/网关、同网络其它容器、访问 host.docker.internal 的源地址、docker0 网关。
_baota_api_allow_ips() {
  local inspected src docker0 nets nid addrs token host_ip
  local -a raw=()
  raw+=("127.0.0.1")
  raw+=("172.17.0.1")
  host_ip="$(_detect_host_ipv4 2>/dev/null || true)"
  [[ -n "$host_ip" ]] && raw+=("$host_ip")

  inspected="$(run_docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{.Gateway}} {{end}} {{.NetworkSettings.IPAddress}} {{.NetworkSettings.Gateway}}' "$FSWAF_CONTAINER" 2>/dev/null || true)"
  if [[ -n "$inspected" ]]; then
    # shellcheck disable=SC2206
    raw+=($inspected)
  fi

  nets="$(run_docker inspect -f '{{range .NetworkSettings.Networks}}{{.NetworkID}} {{end}}' "$FSWAF_CONTAINER" 2>/dev/null || true)"
  for nid in $nets; do
    [[ -n "$nid" ]] || continue
    addrs="$(run_docker network inspect -f '{{range .Containers}}{{.IPv4Address}} {{end}}' "$nid" 2>/dev/null || true)"
    for token in $addrs; do
      token="${token%%/*}"
      [[ -n "$token" ]] && raw+=("$token")
    done
    addrs="$(run_docker network inspect -f '{{range .IPAM.Config}}{{.Gateway}} {{end}}' "$nid" 2>/dev/null || true)"
    if [[ -n "$addrs" ]]; then
      # shellcheck disable=SC2206
      raw+=($addrs)
    fi
  done

  src="$(run_docker exec "$FSWAF_CONTAINER" /opt/venv/bin/python -c 'import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(2);s.connect(("host.docker.internal",9));print(s.getsockname()[0]);s.close()' 2>/dev/null || true)"
  src="$(printf '%s' "$src" | tr -d '\r' | awk 'NF{line=$0} END{print line}')"
  [[ -n "$src" ]] && raw+=("$src")

  docker0="$(run_docker network inspect bridge -f '{{range .IPAM.Config}}{{.Gateway}} {{end}}' 2>/dev/null || true)"
  if [[ -n "$docker0" ]]; then
    # shellcheck disable=SC2206
    raw+=($docker0)
  fi

  printf '%s\n' "${raw[@]}" | awk '/^([0-9]{1,3}\.){3}[0-9]{1,3}$/ && $0 != "0.0.0.0" && !seen[$0]++'
}

_bootstrap_baota_account() {
  local panel_root="/www/server/panel"
  local port ssl_flag scheme url api_file extra key plaintext merged ip_line
  local -a allow_ips=()
  [[ -d "$panel_root" ]] || return 1
  port="$(_read_trim_file "${panel_root}/data/port.pl" || true)"
  [[ -n "$port" ]] || return 1
  ssl_flag="$(_read_trim_file "${panel_root}/data/ssl.pl" || true)"
  scheme="http"
  case "$(printf '%s' "$ssl_flag" | tr '[:upper:]' '[:lower:]')" in
  true | 1 | yes | on) scheme="https" ;;
  esac
  url="${scheme}://host.docker.internal:${port}"
  api_file="${panel_root}/config/api.json"
  extra=""
  key=""
  plaintext="$(openssl rand -hex 16 2>/dev/null || tr -dc 'A-Za-z0-9' </dev/urandom | head -c 24)"
  while IFS= read -r ip_line; do
    [[ -n "$ip_line" ]] && allow_ips+=("$ip_line")
  done < <(_baota_api_allow_ips)
  if [[ ${#allow_ips[@]} -eq 0 ]]; then
    allow_ips=(127.0.0.1 172.17.0.1)
  fi
  info "宝塔 API 白名单将合并：${allow_ips[*]}"
  if [[ -d "$(dirname "$api_file")" ]] && merged="$(_host_python - "$api_file" "$plaintext" "${allow_ips[@]}" <<'PY'
import hashlib, json, sys
path, secret = sys.argv[1], sys.argv[2]
allow = [a.strip() for a in sys.argv[3:] if a.strip()]
if not allow:
    allow = ["127.0.0.1", "172.17.0.1"]
try:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}
token = str(data.get("token") or "").strip()
opened = data.get("open") in (True, "true", "True", 1, "1")
limit = data.get("limit_addr") or []
if isinstance(limit, str):
    ips = [p.strip() for p in limit.replace(",", " ").split() if p.strip()]
elif isinstance(limit, list):
    ips = [str(x).strip() for x in limit if str(x).strip()]
else:
    ips = []
for ip in allow:
    if ip not in ips:
        ips.append(ip)
data["open"] = True
data["limit_addr"] = ips
if opened and token:
    key, prehashed = token, "1"
else:
    data["token"] = hashlib.md5(secret.encode("utf-8")).hexdigest()
    key, prehashed = secret, "0"
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=4)
print(key)
print(prehashed)
PY
  )"; then
    key="$(printf '%s\n' "$merged" | sed -n '1p')"
    if [[ "$(printf '%s\n' "$merged" | sed -n '2p')" == "1" ]]; then
      extra='{"baota_token_prehashed":true}'
    fi
  else
    warn "未能更新宝塔 API 配置（缺少 python 或无法写 api.json），将仅写入面板地址"
  fi
  _write_local_panel_account "baota" "本机宝塔" "$url" "$key" "$extra" "由一键安装自动检测"
}

_onepanel_bin() {
  if command -v 1pctl >/dev/null 2>&1; then
    command -v 1pctl
  elif [[ -x /usr/bin/1pctl ]]; then
    printf '%s\n' /usr/bin/1pctl
  elif [[ -x /usr/local/bin/1pctl ]]; then
    printf '%s\n' /usr/local/bin/1pctl
  else
    return 1
  fi
}

_bootstrap_onepanel_account() {
  local bin db_path url key port scheme ssl_raw info
  bin="$(_onepanel_bin)" || return 1
  db_path=""
  if [[ -f /opt/1panel/db/core.db ]]; then
    db_path="/opt/1panel/db/core.db"
  elif [[ -f /opt/1panel/db/1Panel.db ]]; then
    db_path="/opt/1panel/db/1Panel.db"
  else
    local base
    base="$(grep -E '^BASE_DIR=' "$bin" 2>/dev/null | head -n1 | cut -d= -f2- | tr -d "\"'" | tr -d '\r' || true)"
    [[ -n "$base" ]] || base="/opt"
    if [[ -f "${base}/1panel/db/core.db" ]]; then
      db_path="${base}/1panel/db/core.db"
    elif [[ -f "${base}/1panel/db/1Panel.db" ]]; then
      db_path="${base}/1panel/db/1Panel.db"
    fi
  fi
  port=""
  scheme="http"
  key=""
  if [[ -n "$db_path" ]] && info="$(_host_python - "$db_path" <<'PY'
import json, sqlite3, sys
path = sys.argv[1]
con = sqlite3.connect(path)
cur = con.cursor()
rows = []
for sql in ("SELECT key, value FROM settings", "SELECT param, value FROM settings"):
    try:
        rows = cur.execute(sql).fetchall()
        if rows:
            break
    except Exception:
        continue
data = {str(k): ("" if v is None else str(v)) for k, v in rows}
lower = {k.lower(): v for k, v in data.items()}

def pick(*names):
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return ""

port = pick("ServerPort", "server_port") or "10086"
ssl = pick("SSL", "ssl").lower()
api_status = pick("ApiInterfaceStatus", "api_interface_status").lower()
api_key = pick("ApiKey", "api_key")
if api_status not in {"enable", "enabled", "true", "1"}:
    api_key = ""
print(json.dumps({"port": port, "ssl": ssl, "api_key": api_key}, ensure_ascii=False))
PY
  )"; then
    port="$(_host_python -c 'import json,sys; print(json.loads(sys.argv[1]).get("port") or "")' "$info" 2>/dev/null || true)"
    ssl_raw="$(_host_python -c 'import json,sys; print(json.loads(sys.argv[1]).get("ssl") or "")' "$info" 2>/dev/null || true)"
    key="$(_host_python -c 'import json,sys; print(json.loads(sys.argv[1]).get("api_key") or "")' "$info" 2>/dev/null || true)"
    case "$ssl_raw" in
    enable | enabled | true | 1 | on) scheme="https" ;;
    esac
  fi
  if [[ -z "$port" ]]; then
    local ui
    ui="$("$bin" user-info 2>/dev/null || true)"
    port="$(printf '%s\n' "$ui" | awk -F': *' 'BEGIN{IGNORECASE=1} $1 ~ /^(port|端口)$/ {gsub(/[[:space:]]/,"",$2); print $2; exit}')"
  fi
  [[ -n "$port" ]] || port="10086"
  # API 只要协议+主机+端口；安全入口是浏览器 UI 路径，写入后反而干扰展示。
  url="${scheme}://host.docker.internal:${port}"
  _write_local_panel_account "onepanel" "本机 1Panel" "$url" "$key" "" "由一键安装自动检测"
}

bootstrap_host_panels() {
  info "检测本机宝塔 / 1Panel..."
  local found=0
  if [[ -d /www/server/panel && -f /www/server/panel/data/port.pl ]]; then
    found=1
    _bootstrap_baota_account || warn "写入本机宝塔账号失败（不影响安装）"
  fi
  if _onepanel_bin >/dev/null 2>&1; then
    found=1
    _bootstrap_onepanel_account || warn "写入本机 1Panel 账号失败（不影响安装）"
  fi
  if [[ "$found" -eq 0 ]]; then
    info "未检测到宝塔或 1Panel，跳过面板账号写入"
  fi
}

print_success() {
  local kind="${1:-install}" # install | update
  local title panel_port host_hint host_ip panel_url
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"
  host_hint="<服务器IP>"
  if host_ip="$(_detect_host_ipv4 2>/dev/null)"; then
    host_hint="$host_ip"
  elif [[ "$OS_FAMILY" == "darwin" ]]; then
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
  ui_row "文档  ${FSWAF_SITE}/guide/upgrade-backup"
  ui_line m
  ui_row "${c_bold}${FSWAF_PRODUCT}${c_reset} ${c_dim}${FSWAF_SLOGAN}${c_reset}"
  ui_line b

  if [[ "$kind" == "install" && -n "$NGINX_MOVED_HTTP" ]]; then
    echo
    info "本地网站已改为 HTTP ${NGINX_MOVED_HTTP} / HTTPS ${NGINX_MOVED_HTTPS}，回源请填新端口"
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
    echo
    warn "当前目录不是 git 仓库，无法 git pull。"
    if confirm "是否下载最新代码并覆盖项目文件？（保留 .env，站点数据在 Docker 卷中不受影响）" "Y"; then
      overlay_project_from_fresh_clone || true
    else
      warn "已跳过代码更新，将使用当前目录现有代码构建"
    fi
  fi

  merge_missing_env_from_example
  sync_jwt_refresh_ttl
  build_and_start
  wait_healthy
  bootstrap_host_panels || warn "检测本机面板失败（不影响安装）"
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
    sync_jwt_refresh_ttl
  else
    write_env_file
  fi
  write_meta
  build_and_start
  wait_healthy
  bootstrap_host_panels || warn "检测本机面板失败（不影响安装）"
  print_success install
}

# ---------------------------------------------------------------------------
# 命令行参数
# ---------------------------------------------------------------------------

print_usage() {
  cat <<EOF
${FSWAF_PRODUCT} 一键安装 / 更新脚本 v${FSWAF_VERSION}

用法：
  curl -fsSL ${FSWAF_SITE}/install.sh | bash
  bash install.sh

安装过程中会询问是否启用国内加速（国内服务器选 Y，海外选 N）。

非交互模式（FSWAF_ASSUME_YES=1）默认海外直连；需国内加速可设 FSWAF_CN_MIRROR=1。

官网：${FSWAF_SITE}
EOF
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

main() {
  case "${1:-}" in
  -h | --help)
    print_usage
    exit 0
    ;;
  "")
    ;;
  *)
    die "未知参数：$1（使用 --help 查看用法）"
    ;;
  esac
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

  # 依赖装好后重新判定一次（例如刚装好 docker 才能看到容器；重选目录后也可能变为更新）
  detect_mode_and_dir
  # Docker Hub 加速需 dockerd 已就绪，询问本身已在确认路径后完成
  prompt_cn_mirror_choice

  if [[ "${FSWAF_CN_MIRROR:-}" == "1" ]]; then
    apply_china_mirror_settings
  fi

  if [[ "$MODE" == "update" ]]; then
    run_update
  else
    run_install
  fi
}

main "$@"
