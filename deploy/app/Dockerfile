# 流盾WAF 应用镜像：后端 + Worker + 引擎 + 面板（同一容器，supervisord 管理）
# Redis / ClickHouse 使用官方镜像单独运行；SQLite 内嵌于 app 卷，见 docker-compose.yml
# syntax=docker/dockerfile:1

# ---- 1) 构建前端 ----
FROM node:20-alpine AS frontend-build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- 2) 应用运行镜像（基于已有 OpenResty 引擎镜像，避免重复装系统包）----
FROM openresty/openresty:1.25.3.1-2-alpine-fat

# 默认清华 PyPI 镜像，加速国内 docker build；海外可覆盖：
#   docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple --build-arg PIP_TRUSTED_HOST= app
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_PROGRESS_BAR=on \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

RUN apk add --no-cache python3 py3-pip nginx supervisor curl redis libjpeg-turbo tzdata

# OpenResty fat 镜像仅含旧版 GeoIP(.dat) 模块，不含 GeoIP2(.mmdb)；编译动态模块以启用地理字段。
# 模块源码已 vendored（避免构建时依赖 GitHub）；nginx 版本取 openresty/x.y.z.N → x.y.z。
COPY deploy/app/vendor/ngx_http_geoip2_module /tmp/ngx_http_geoip2_module
RUN apk add --no-cache --virtual .geoip2-build \
        build-base pcre-dev zlib-dev openssl-dev linux-headers libmaxminddb-dev curl \
    && openresty_ver=$(/usr/local/openresty/nginx/sbin/nginx -v 2>&1 | sed -n 's/.*openresty\///p' | cut -d' ' -f1) \
    && nginx_version=$(echo "$openresty_ver" | cut -d. -f1-3) \
    && test -n "$nginx_version" \
    && echo "building geoip2 against nginx ${nginx_version} (openresty ${openresty_ver})" \
    && cd /tmp \
    && curl -fsSL --retry 5 --retry-delay 2 \
         -o "nginx-${nginx_version}.tar.gz" \
         "https://nginx.org/download/nginx-${nginx_version}.tar.gz" \
    && tar xzf "nginx-${nginx_version}.tar.gz" \
    && cd "nginx-${nginx_version}" \
    && ./configure --with-compat --add-dynamic-module=/tmp/ngx_http_geoip2_module \
    && make -j"$(nproc)" modules \
    && cp objs/ngx_http_geoip2_module.so /usr/local/openresty/nginx/modules/ \
    && cd / \
    && rm -rf /tmp/nginx-* /tmp/ngx_http_geoip2_module \
    && apk del .geoip2-build \
    && apk add --no-cache libmaxminddb

# 后端：分层安装 Python 依赖——base 层缓存稳定包，extra 层仅装新增包
WORKDIR /app/backend
COPY backend/requirements-base.txt backend/requirements-extra.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    echo "==> [base] installing stable Python deps (skipped when requirements-base.txt unchanged)..." \
    && apk add --no-cache --virtual .py-build-deps python3-dev gcc musl-dev jpeg-dev zlib-dev \
    && python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements-base.txt \
    && apk del .py-build-deps
RUN --mount=type=cache,target=/root/.cache/pip \
    echo "==> [extra] installing incremental deps (only when requirements-extra.txt changes)..." \
    && /opt/venv/bin/pip install -r requirements-extra.txt
COPY backend/pyproject.toml ./
COPY backend/app ./app
COPY slide_captcha /opt/flowshield/slide-captcha-defaults
COPY deploy/clickhouse /app/deploy/clickhouse

# WAF 引擎
COPY engine/lua /etc/nginx/lua
COPY engine/snippets /etc/nginx/snippets
COPY deploy/app/engine.nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
RUN mkdir -p /etc/nginx/html /data/engine/conf.d /data/engine/certs /etc/nginx/geoip \
    /usr/local/openresty/nginx/logs \
    && touch /usr/local/openresty/nginx/logs/error.log \
    && chmod 666 /usr/local/openresty/nginx/logs/error.log \
    && rm -rf /etc/nginx/conf.d/*

# 管理面板
COPY --from=frontend-build /build/dist /usr/share/nginx/html
COPY deploy/app/frontend.nginx.conf /etc/nginx/http.d/flowshield-panel.conf
COPY deploy/app/panel.nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/http.d/default.conf 2>/dev/null || true

# 进程管理
COPY deploy/app/supervisord.conf /etc/supervisor/supervisord.conf
COPY deploy/app/entrypoint.sh /entrypoint.sh
COPY deploy/app/wait-for.sh /opt/flowshield/wait-for.sh
COPY deploy/app/wait-for-backend.sh /opt/flowshield/wait-for-backend.sh
RUN chmod +x /entrypoint.sh /opt/flowshield/wait-for.sh /opt/flowshield/wait-for-backend.sh

EXPOSE 80 443 9000

VOLUME ["/data/engine/conf.d", "/data/engine/certs"]

ENTRYPOINT ["/entrypoint.sh"]
