# syntax=docker/dockerfile:1
#
# 流盾 WAF 应用镜像：后端 + Worker + OpenResty 引擎 + 管理面板
# （同一容器，由 supervisord 管理）
#
# Redis / ClickHouse 使用 Compose 官方镜像单独运行。
# SQLite 位于 /data/waf.db，见 docker-compose.yml 的 app_data 卷。
#
# 构建阶段说明（安装日志由 BuildKit/Compose 进度展示，此处不写 echo 避免干扰 TUI）：
#   1. frontend-build：npm ci + Vite 打包
#   2. runtime：OpenResty 基础镜像 + apk 系统包（首次约 3–10 分钟，视网络而定）
#   3. GeoIP2 动态模块编译
#   4. Python base/extra 分层 pip 安装
#
# RUN 尽量拆成单条命令：构建失败时 BuildKit 会标出具体步骤号，便于定位。

# ---- 1. 前端构建 ----
FROM node:20-alpine AS frontend-build
ARG NPM_CONFIG_REGISTRY=
WORKDIR /build

# vite 在 devDependencies。NODE_ENV=development 且 NPM_CONFIG_PRODUCTION=false，
# 避免 npm 在生产模式下 omit=dev。NPM_CONFIG_REGISTRY 可由 compose 传入（如 npmmirror）。
ENV NODE_ENV=development \
    NPM_CONFIG_PRODUCTION=false \
    NPM_CONFIG_REGISTRY=${NPM_CONFIG_REGISTRY}

# 先只复制 lockfile：未变更时跳过 npm ci，复用 node_modules 缓存。
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --include=dev
RUN test -f node_modules/.bin/vite
RUN mv node_modules /tmp/frontend-node_modules

# COPY frontend/ 前把依赖移出 /build。部分 Docker/BuildKit 会用构建上下文里的
# 空 node_modules 盖掉已安装的 vite（.dockerignore 排除空目录并不总生效）。
# 不能在 Dockerfile 里「先删宿主机 frontend/node_modules 再 COPY」：
# COPY 读的是构建开始时已打包的上下文。
COPY frontend/ ./
RUN rm -rf node_modules
RUN mv /tmp/frontend-node_modules node_modules
RUN npm run build

# ---- 2. 运行镜像 ----
# 基于 OpenResty Alpine fat，避免再装一套系统包。
FROM openresty/openresty:1.25.3.1-2-alpine-fat

# 默认清华 PyPI，加速国内 docker build。海外可覆盖：
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple --build-arg PIP_TRUSTED_HOST= app
# Alpine 源默认官方；仅 apk 慢/失败时再指定：
#   --build-arg ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
# 构建容器无法访问外网 apk 源时，Linux 宿主机可用 host 网络构建，见 docker-compose.yml。
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG ALPINE_MIRROR=

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PROGRESS_BAR=off \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

# ---- 3. 系统依赖 ----
RUN if [ -n "${ALPINE_MIRROR}" ]; then \
      sed -i "s#https\\?://dl-cdn.alpinelinux.org/alpine#${ALPINE_MIRROR}#g" /etc/apk/repositories; \
    fi
RUN if [ -n "${ALPINE_MIRROR}" ]; then \
      sed -i "s#https\\?://[^/]*/alpine#${ALPINE_MIRROR}#g" /etc/apk/repositories; \
    fi
RUN apk add --no-cache python3 py3-pip nginx supervisor curl redis libjpeg-turbo tzdata

# ---- 4. GeoIP2 动态模块 ----
# OpenResty fat 仅含旧版 GeoIP(.dat)，不含 GeoIP2(.mmdb)；需编译动态模块才能用地理字段。
# 模块源码已 vendored 到 deploy/app/vendor/ngx_http_geoip2_module，避免构建时拉 GitHub。
# nginx 版本由 openresty/x.y.z.N 截取为 x.y.z，再下载对应 nginx 源码做 --with-compat 编译。
COPY deploy/app/vendor/ngx_http_geoip2_module /tmp/ngx_http_geoip2_module
RUN apk add --no-cache --virtual .geoip2-build \
        build-base pcre-dev zlib-dev openssl-dev linux-headers libmaxminddb-dev curl
RUN /usr/local/openresty/nginx/sbin/nginx -v 2>&1 \
    | sed -n 's/.*openresty\///p' \
    | cut -d' ' -f1 \
    > /tmp/openresty_ver
RUN cut -d. -f1-3 /tmp/openresty_ver > /tmp/nginx_build_version
RUN test -s /tmp/nginx_build_version
RUN curl -fsSL --retry 5 --retry-delay 2 \
    -o "/tmp/nginx-$(cat /tmp/nginx_build_version).tar.gz" \
    "https://nginx.org/download/nginx-$(cat /tmp/nginx_build_version).tar.gz"
RUN tar xzf "/tmp/nginx-$(cat /tmp/nginx_build_version).tar.gz" -C /tmp
RUN cd "/tmp/nginx-$(cat /tmp/nginx_build_version)" \
    && ./configure --with-compat --add-dynamic-module=/tmp/ngx_http_geoip2_module
RUN make -C "/tmp/nginx-$(cat /tmp/nginx_build_version)" -j"$(nproc)" modules
RUN cp "/tmp/nginx-$(cat /tmp/nginx_build_version)/objs/ngx_http_geoip2_module.so" \
    /usr/local/openresty/nginx/modules/
RUN rm -rf /tmp/nginx-* /tmp/ngx_http_geoip2_module /tmp/openresty_ver /tmp/nginx_build_version
RUN apk del .geoip2-build
RUN apk add --no-cache libmaxminddb

# ---- 5. Python 依赖（分层安装） ----
# base：稳定包，requirements-base.txt 不变则整层缓存。
# extra：增量包，仅 requirements-extra.txt 变化时重装。
# MAKEFLAGS/CARGO 固定 -j1，避免小内存机器编译时 OOM。
WORKDIR /app/backend
COPY backend/requirements-base.txt backend/requirements-extra.txt ./
RUN apk add --no-cache --virtual .py-build-deps \
        python3-dev gcc musl-dev jpeg-dev zlib-dev rust cargo
RUN python3 -m venv /opt/venv
RUN /opt/venv/bin/pip install --upgrade pip
RUN --mount=type=cache,target=/root/.cache/pip \
    MAKEFLAGS="-j1" CARGO_BUILD_JOBS=1 \
    /opt/venv/bin/pip install --prefer-binary --quiet -r requirements-base.txt
RUN apk del .py-build-deps
RUN --mount=type=cache,target=/root/.cache/pip \
    MAKEFLAGS="-j1" CARGO_BUILD_JOBS=1 \
    /opt/venv/bin/pip install --prefer-binary --quiet -r requirements-extra.txt

# ---- 6. 后端代码与静态资源 ----
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY slide_captcha /opt/flowshield/slide-captcha-defaults
COPY deploy/clickhouse /app/deploy/clickhouse

# ---- 7. WAF 引擎 ----
COPY engine/lua /etc/nginx/lua
COPY engine/snippets /etc/nginx/snippets
COPY deploy/app/engine.nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
RUN mkdir -p /etc/nginx/html /data/engine/conf.d /data/engine/certs /etc/nginx/geoip \
    /usr/local/openresty/nginx/logs
RUN touch /usr/local/openresty/nginx/logs/error.log
RUN chmod 666 /usr/local/openresty/nginx/logs/error.log
RUN rm -rf /etc/nginx/conf.d/*

# ---- 8. 管理面板 ----
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY deploy/app/frontend.nginx.conf /etc/nginx/http.d/flowshield-panel.conf
COPY deploy/app/panel.nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/http.d/default.conf

# ---- 9. 进程管理与启动脚本 ----
COPY deploy/app/supervisord.conf /etc/supervisor/supervisord.conf
COPY deploy/app/entrypoint.sh /entrypoint.sh
COPY deploy/app/wait-for.sh /opt/flowshield/wait-for.sh
COPY deploy/app/wait-for-backend.sh /opt/flowshield/wait-for-backend.sh
COPY deploy/app/startup-log.sh /opt/flowshield/startup-log.sh
COPY deploy/app/startup-ready.sh /opt/flowshield/startup-ready.sh
RUN chmod +x /entrypoint.sh
RUN chmod +x /opt/flowshield/wait-for.sh
RUN chmod +x /opt/flowshield/wait-for-backend.sh
RUN chmod +x /opt/flowshield/startup-log.sh
RUN chmod +x /opt/flowshield/startup-ready.sh

EXPOSE 80 443 9000

# 不在此声明 VOLUME：conf/certs 已并入 compose 的 app_data:/data。
# 若保留子路径 VOLUME，Docker 会自动挂匿名卷，盖住 app_data 内同名目录。
ENTRYPOINT ["/entrypoint.sh"]
