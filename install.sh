#!/usr/bin/env bash
# 流盾 WAF (Flow Shield WAF) 一键安装 / 更新脚本
#
# 推荐：curl -fsSL https://fswaf.top/install.sh | bash
# 备用：curl -fsSL https://raw.githubusercontent.com/Qinver-china/flow-shield-waf/main/install.sh | bash
#
# 官网：https://fswaf.top
set -euo pipefail

FSWAF_VERSION="1.0.0"
FSWAF_PRODUCT="流盾 WAF (Flow Shield WAF)"
FSWAF_SITE="https://fswaf.top"
FSWAF_REPO_URL="${FSWAF_REPO_URL:-https://github.com/Qinver-china/flow-shield-waf.git}"
FSWAF_REPO_DIR_NAME="flow-shield-waf"
FSWAF_CONTAINER="flowshield-waf-app"
FSWAF_COMPOSE_NAME="flowshield-waf"
FSWAF_META_FILE=".flowshield-install"
FSWAF_DEFAULT_HTTP_ALT=8080
FSWAF_DEFAULT_HTTPS_ALT=4343

# ---------------------------------------------------------------------------
# 输出
# ---------------------------------------------------------------------------

c_reset=""
c_bold=""
c_green=""
c_yellow=""
c_red=""
c_cyan=""
if [[ -t 1 ]]; then
  c_reset=$'\033[0m'
  c_bold=$'\033[1m'
  c_green=$'\033[32m'
  c_yellow=$'\033[33m'
  c_red=$'\033[31m'
  c_cyan=$'\033[36m'
fi

info()  { printf '%s\n' "${c_cyan}==>${c_reset} $*"; }
ok()    { printf '%s\n' "${c_green}[OK]${c_reset} $*"; }
warn()  { printf '%s\n' "${c_yellow}[警告]${c_reset} $*"; }
err()   { printf '%s\n' "${c_red}[错误]${c_reset} $*" >&2; }
die()   { err "$*"; exit 1; }

confirm() {
  local prompt="${1:-继续？}"
  local default="${2:-Y}"
  local ans
  if [[ "${FSWAF_ASSUME_YES:-}" == "1" ]]; then
    return 0
  fi
  if [[ "$default" == "Y" ]]; then
    read -r -p "$prompt [Y/n] " ans || true
    [[ -z "$ans" || "$ans" =~ ^[Yy] ]]
  else
    read -r -p "$prompt [y/N] " ans || true
    [[ "$ans" =~ ^[Yy] ]]
  fi
}

# ---------------------------------------------------------------------------
# 系统信息
# ---------------------------------------------------------------------------

OS_FAMILY="unknown"   # linux | darwin
OS_ID=""              # ubuntu | debian | centos | rhel | fedora | amzn | ...
ARCH="$(uname -m 2>/dev/null || echo unknown)"
HAVE_DOCKER=0
HAVE_COMPOSE=0
HAVE_GIT=0
COMPOSE_CMD=()
MODE="install"        # install | update
INSTALL_DIR=""
NGINX_MOVED_HTTP=""
NGINX_MOVED_HTTPS=""

detect_os() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || true)"
  case "$uname_s" in
    Linux*)  OS_FAMILY="linux" ;;
    Darwin*) OS_FAMILY="darwin" ;;
    *)       OS_FAMILY="unsupported" ;;
  esac
  if [[ "$OS_FAMILY" == "linux" && -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-}"
  elif [[ "$OS_FAMILY" == "darwin" ]]; then
    OS_ID="macos"
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
    x86_64|amd64|arm64|aarch64) return 0 ;;
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

refresh_tool_status() {
  HAVE_DOCKER=0
  HAVE_COMPOSE=0
  HAVE_GIT=0
  COMPOSE_CMD=()

  if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      HAVE_DOCKER=1
    else
      HAVE_DOCKER=2  # 已安装但守护进程不可用
    fi
  fi

  if [[ "$HAVE_DOCKER" -eq 1 ]]; then
    if docker compose version >/dev/null 2>&1; then
      HAVE_COMPOSE=1
      COMPOSE_CMD=(docker compose)
    elif command -v docker-compose >/dev/null 2>&1; then
      HAVE_COMPOSE=1
      COMPOSE_CMD=(docker-compose)
    fi
  fi

  if command -v git >/dev/null 2>&1; then
    HAVE_GIT=1
  fi
}

tool_status_line() {
  local name="$1" flag="$2" extra="${3:-}"
  if [[ "$flag" -eq 1 ]]; then
    printf '  %-16s %s%s\n' "$name" "${c_green}已就绪${c_reset}" "$extra"
  elif [[ "$flag" -eq 2 ]]; then
    printf '  %-16s %s%s\n' "$name" "${c_yellow}已安装但未运行${c_reset}" "$extra"
  else
    printf '  %-16s %s%s\n' "$name" "${c_red}未检测到${c_reset}" "$extra"
  fi
}

print_banner() {
  cat <<EOF

${c_bold}============================================================${c_reset}
  ${c_bold}${FSWAF_PRODUCT}${c_reset}
  官网：${c_cyan}${FSWAF_SITE}${c_reset}
  脚本版本：${FSWAF_VERSION}
============================================================

EOF
}

print_precheck_report() {
  echo "${c_bold}环境检测结果${c_reset}"
  printf '  %-16s %s\n' "操作系统" "${OS_FAMILY}/${OS_ID:-?} (${ARCH})"
  printf '  %-16s %s\n' "当前目录" "$(pwd)"
  tool_status_line "Docker" "$HAVE_DOCKER"
  tool_status_line "Docker Compose" "$HAVE_COMPOSE"
  tool_status_line "Git" "$HAVE_GIT"
  echo
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
  docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$FSWAF_CONTAINER"
}

resolve_install_dir_from_container() {
  local geoip_src project
  geoip_src="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/nginx/geoip"}}{{.Source}}{{end}}{{end}}' "$FSWAF_CONTAINER" 2>/dev/null || true)"
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

confirm_workdir() {
  echo "${c_bold}工作目录确认${c_reset}"
  echo "  当前路径：$(pwd)"
  if [[ "$MODE" == "update" && -n "$INSTALL_DIR" ]]; then
    echo "  检测到已安装目录：$INSTALL_DIR"
    echo
    echo "  更新将在已安装目录中执行（git pull + 本地重建）。"
    echo
    if ! confirm "确认更新该安装目录？" "Y"; then
      echo "已取消。"
      exit 0
    fi
    return 0
  fi

  echo
  if [[ "$MODE" == "install" ]]; then
    echo "  首次安装将在此目录下创建/使用 ${FSWAF_REPO_DIR_NAME}/"
  else
    echo "  更新将在已安装的项目目录中执行（git pull + 本地重建）。"
  fi
  echo
  if ! confirm "确认在此路径继续？" "Y"; then
    echo
    echo "请先 cd 到目标目录后再执行本脚本。"
    echo "  推荐：curl -fsSL ${FSWAF_SITE}/install.sh | bash"
    echo "  备用：curl -fsSL https://raw.githubusercontent.com/Qinver-china/flow-shield-waf/main/install.sh | bash"
    exit 0
  fi
}

# ---------------------------------------------------------------------------
# 依赖安装
# ---------------------------------------------------------------------------

install_git_linux() {
  info "安装 Git..."
  case "$OS_ID" in
    ubuntu|debian|linuxmint|pop)
      need_sudo apt-get update -y
      need_sudo apt-get install -y git
      ;;
    centos|rhel|rocky|almalinux|ol)
      if command -v dnf >/dev/null 2>&1; then
        need_sudo dnf install -y git
      else
        need_sudo yum install -y git
      fi
      ;;
    fedora)
      need_sudo dnf install -y git
      ;;
    amzn)
      need_sudo yum install -y git
      ;;
    *)
      if command -v apt-get >/dev/null 2>&1; then
        need_sudo apt-get update -y
        need_sudo apt-get install -y git
      elif command -v dnf >/dev/null 2>&1; then
        need_sudo dnf install -y git
      elif command -v yum >/dev/null 2>&1; then
        need_sudo yum install -y git
      else
        die "无法自动安装 Git，请手动安装后重试。"
      fi
      ;;
  esac
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
      ubuntu|debian|linuxmint|pop) need_sudo apt-get update -y && need_sudo apt-get install -y curl ca-certificates ;;
      *) die "需要 curl 才能自动安装 Docker，请先安装 curl。" ;;
    esac
  fi
  curl -fsSL https://get.docker.com | need_sudo sh
  if command -v systemctl >/dev/null 2>&1; then
    need_sudo systemctl enable --now docker || true
  fi
  if [[ "$(id -u)" -ne 0 ]]; then
    need_sudo usermod -aG docker "$(id -un)" || true
    warn "已将当前用户加入 docker 组。若随后 docker 命令仍无权限，请重新登录 SSH 后再执行本脚本。"
  fi
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
  info "脚本将尝试自动安装缺失的基础环境（Docker / Docker Compose / Git）。"
  if ! confirm "允许自动安装缺失组件？" "Y"; then
    echo
    echo "请手动安装后再执行本脚本："
    echo "  - Docker + Compose：https://docs.docker.com/engine/install/"
    echo "  - Git：各发行版软件源或 https://git-scm.com/"
    echo "  - macOS：请先安装 Docker Desktop，并确保其正在运行"
    exit 0
  fi

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
    info "尝试启动 Docker 服务..."
    if command -v systemctl >/dev/null 2>&1; then
      need_sudo systemctl start docker || true
    fi
  fi

  refresh_tool_status

  if [[ "$HAVE_DOCKER" -eq 1 && "$HAVE_COMPOSE" -ne 1 ]]; then
    warn "Docker 可用但未检测到 Compose。Linux 可尝试：sudo apt-get install -y docker-compose-plugin"
    if [[ "$OS_FAMILY" == "linux" ]]; then
      case "$OS_ID" in
        ubuntu|debian|linuxmint|pop)
          need_sudo apt-get update -y || true
          need_sudo apt-get install -y docker-compose-plugin || true
          ;;
      esac
      refresh_tool_status
    fi
  fi

  [[ "$HAVE_GIT" -eq 1 ]] || die "Git 仍不可用"
  [[ "$HAVE_DOCKER" -eq 1 ]] || die "Docker 仍不可用（请确认守护进程已启动）"
  [[ "$HAVE_COMPOSE" -eq 1 ]] || die "Docker Compose 仍不可用"
  ok "基础环境已就绪"
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
    /opt/homebrew/etc/nginx
  do
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

handle_ports_for_install() {
  local http_port=80 https_port=443 panel_port=9000
  local busy=0

  info "检查端口 ${http_port}/${https_port}/${panel_port}..."

  if port_in_use "$panel_port"; then
    warn "面板端口 ${panel_port} 已被占用："
    port_pids "$panel_port" || true
    echo
    if confirm "是否改用其他面板端口？" "Y"; then
      local new_panel
      read -r -p "新的面板端口 [9001]: " new_panel || true
      panel_port="${new_panel:-9001}"
      if port_in_use "$panel_port"; then
        die "端口 ${panel_port} 仍被占用，请释放后再试。"
      fi
      export FSWAF_PANEL_PORT="$panel_port"
    else
      die "请先释放 ${panel_port} 后再安装。"
    fi
  fi

  if port_in_use "$http_port" || port_in_use "$https_port"; then
    busy=1
    echo
    warn "检测到 80/443 被占用："
    port_in_use "$http_port" && { echo "--- :${http_port} ---"; port_pids "$http_port" || true; }
    port_in_use "$https_port" && { echo "--- :${https_port} ---"; port_pids "$https_port" || true; }
    echo
  fi

  if [[ "$busy" -eq 0 ]]; then
    ok "80/443 空闲"
    return 0
  fi

  if port_holder_is_nginx "$http_port" || port_holder_is_nginx "$https_port" || command -v nginx >/dev/null 2>&1; then
    info "疑似 Nginx/宝塔占用。可自动把 Nginx 的 listen 80/443 改到其他端口，把 80/443 留给流盾。"
    if confirm "是否自动调整 Nginx 监听端口？" "Y"; then
      local new_http new_https
      read -r -p "Nginx 新的 HTTP 端口 [${FSWAF_DEFAULT_HTTP_ALT}]: " new_http || true
      read -r -p "Nginx 新的 HTTPS 端口 [${FSWAF_DEFAULT_HTTPS_ALT}]: " new_https || true
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
      ok "80/443 已释放"
      return 0
    fi
  fi

  echo
  err "请先停止或改掉占用 80/443 的程序后重试。常见处理："
  echo "  - 宝塔：把网站监听改为高位端口（如 ${FSWAF_DEFAULT_HTTP_ALT}/${FSWAF_DEFAULT_HTTPS_ALT}）"
  echo "  - 其它 Web 服务器：修改 listen 或停止服务"
  echo "  - 其它容器：docker ps 查看后 stop/改端口"
  exit 1
}

# ---------------------------------------------------------------------------
# 获取代码 / 生成 .env
# ---------------------------------------------------------------------------

ensure_repo() {
  if [[ -n "$INSTALL_DIR" && -d "$INSTALL_DIR" ]]; then
    cd "$INSTALL_DIR"
    return 0
  fi

  if is_project_root "."; then
    INSTALL_DIR="$(pwd)"
    return 0
  fi

  if [[ -d "$FSWAF_REPO_DIR_NAME" ]] && is_project_root "$FSWAF_REPO_DIR_NAME"; then
    INSTALL_DIR="$(cd "$FSWAF_REPO_DIR_NAME" && pwd)"
    cd "$INSTALL_DIR"
    info "使用已有目录：$INSTALL_DIR"
    return 0
  fi

  info "克隆仓库：${FSWAF_REPO_URL}"
  git clone --depth 1 "$FSWAF_REPO_URL" "$FSWAF_REPO_DIR_NAME"
  INSTALL_DIR="$(cd "$FSWAF_REPO_DIR_NAME" && pwd)"
  cd "$INSTALL_DIR"
  ok "代码已就绪：$INSTALL_DIR"
}

prompt_admin_credentials() {
  local user pass pass2
  echo
  echo "${c_bold}设置管理面板账号（其余密钥将自动随机生成）${c_reset}"
  read -r -p "管理员账号 [admin]: " user || true
  user="${user:-admin}"
  while true; do
    read -r -s -p "管理员密码: " pass || true
    echo
    [[ -n "$pass" ]] || { warn "密码不能为空"; continue; }
    [[ "${#pass}" -ge 6 ]] || { warn "密码至少 6 位"; continue; }
    read -r -s -p "再次确认密码: " pass2 || true
    echo
    [[ "$pass" == "$pass2" ]] && break
    warn "两次输入不一致，请重试"
  done
  FSWAF_ADMIN_USER="$user"
  FSWAF_ADMIN_PASSWORD="$pass"
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

  cat > .env <<EOF
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
WAF_ALLOW_INSECURE_DEFAULTS=false

PANEL_PORT=${panel_port}

WAF_HTTP_PORT=80
WAF_HTTPS_PORT=443
WAF_ORIGIN_HOST_GATEWAY=${gateway}
EOF

  ok "已生成 .env（密钥已随机；管理员账号由你设置）"
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
    echo "${key}=${val}" >> .env
    info "已向 .env 追加新变量：${key}"
  done < .env.example
}

write_meta() {
  cat > "$FSWAF_META_FILE" <<EOF
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
  "${COMPOSE_CMD[@]}" "$@"
}

build_and_start() {
  info "拉取依赖镜像并本地构建启动（首次可能较久）..."
  compose up -d --build
  ok "容器已启动"
}

wait_healthy() {
  local panel_port i
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"

  info "等待健康检查（最长约 3 分钟）..."
  for i in $(seq 1 36); do
    if curl -fsS "http://127.0.0.1:${panel_port}/health" >/dev/null 2>&1 \
      && curl -fsS "http://127.0.0.1/waf-health" >/dev/null 2>&1; then
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
  local panel_port host_hint
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"
  host_hint="<服务器IP>"
  if [[ "$OS_FAMILY" == "darwin" ]]; then
    host_hint="127.0.0.1"
  fi

  cat <<EOF

${c_bold}${c_green}============================================================
  部署完成
============================================================${c_reset}

  产品：${FSWAF_PRODUCT}
  官网：${FSWAF_SITE}
  目录：$(pwd)

  管理面板：http://${host_hint}:${panel_port}
  管理员：  ${FSWAF_ADMIN_USER:-（见 .env 中 WAF_ADMIN_USER）}

EOF

  if [[ -n "$NGINX_MOVED_HTTP" ]]; then
    cat <<EOF
  已将本机 Nginx 监听调整为：
    HTTP  ${NGINX_MOVED_HTTP}
    HTTPS ${NGINX_MOVED_HTTPS}
  在流盾面板添加站点回源时，请填写上述端口（不要再填 80/443）。

EOF
  fi

  cat <<EOF
  下一步：打开面板 → 接入站点 / 配置证书 / 修改 DNS
  文档：${FSWAF_SITE}/guide/first-site

  以后在本机更新，可在任意目录执行同一命令（推荐链接）：
    curl -fsSL ${FSWAF_SITE}/install.sh | bash

EOF
}

# ---------------------------------------------------------------------------
# 更新流程
# ---------------------------------------------------------------------------

run_update() {
  if [[ -z "$INSTALL_DIR" ]]; then
    echo
    warn "检测到已有 ${FSWAF_CONTAINER} 容器，但未能自动定位项目目录。"
    read -r -p "请输入流盾项目根目录路径: " INSTALL_DIR || true
    [[ -n "$INSTALL_DIR" ]] || die "未提供目录"
  fi
  cd "$INSTALL_DIR" || die "无法进入：$INSTALL_DIR"
  is_project_root "." || die "目录不像流盾项目根（缺少 docker-compose.yml / name: ${FSWAF_COMPOSE_NAME}）：$(pwd)"

  [[ -f .env ]] || die "未找到 .env，无法更新。若需重装请先处理旧容器后重新安装。"

  info "更新模式：$(pwd)"
  cp .env ".env.bak.$(date +%Y%m%d%H%M%S)"
  ok "已备份 .env"

  if [[ -d .git ]]; then
    info "拉取最新代码..."
    git pull --ff-only origin main || git pull --ff-only || warn "git pull 未完全成功，将继续尝试用当前代码构建"
  else
    warn "当前目录不是 git 仓库，跳过 pull（若用压缩包部署请自行覆盖代码并保留 .env）"
  fi

  merge_missing_env_from_example
  build_and_start
  wait_healthy
  write_meta

  local panel_port
  panel_port="$(grep -E '^PANEL_PORT=' .env 2>/dev/null | cut -d= -f2 | tr -d '\r' || true)"
  panel_port="${panel_port:-9000}"

  cat <<EOF

${c_bold}${c_green}更新完成${c_reset}
  目录：$(pwd)
  面板：http://127.0.0.1:${panel_port}
  说明：https://fswaf.top/guide/upgrade-backup

EOF
}

# ---------------------------------------------------------------------------
# 首次安装流程
# ---------------------------------------------------------------------------

run_install() {
  handle_ports_for_install
  ensure_repo
  if [[ -f .env ]]; then
    warn "目录中已存在 .env，将保留并直接启动（不覆盖密钥）。"
    if ! confirm "继续使用现有 .env 启动？" "Y"; then
      die "已取消。如需重新生成，请先备份并删除 .env 后再执行。"
    fi
  else
    prompt_admin_credentials
    write_env_file
  fi
  write_meta
  build_and_start
  wait_healthy
  # 安装成功后再读一遍账号用于展示
  FSWAF_ADMIN_USER="$(grep -E '^WAF_ADMIN_USER=' .env | cut -d= -f2- | tr -d '\r')"
  print_success
}

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

main() {
  detect_os
  print_banner

  if [[ "$OS_FAMILY" == "unsupported" ]]; then
    die "当前系统不受支持。请在 Linux 服务器、宝塔环境或 macOS（Docker Desktop）上执行。"
  fi

  check_arch
  check_resources
  refresh_tool_status
  print_precheck_report

  detect_mode_and_dir
  if [[ "$MODE" == "update" ]]; then
    info "判定结果：${c_bold}更新${c_reset}（检测到已有安装或 ${FSWAF_CONTAINER} 容器）"
  else
    info "判定结果：${c_bold}首次安装${c_reset}"
  fi
  echo

  confirm_workdir

  if [[ "$MODE" == "install" ]]; then
    echo
    info "继续后将：检测/安装 Docker·Compose·Git → 处理 80/443 → 克隆代码并本地构建。"
  else
    echo
    info "继续后将：确认依赖 → 备份 .env → 拉取代码 → 本地重建。"
  fi
  if ! confirm "确认继续？" "Y"; then
    echo "已取消。也可按文档手动安装：${FSWAF_SITE}/guide/deploy-server"
    exit 0
  fi

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
