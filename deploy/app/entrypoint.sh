#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=/opt/flowshield/startup-log.sh
source /opt/flowshield/startup-log.sh
startup_init
startup_header

mkdir -p /data/engine/conf.d /data/engine/certs /var/log/supervisor /etc/flowshield /etc/nginx/geoip /run/flowshield
rm -f /run/flowshield/backend.sock

startup_step "1/5" "初始化运行环境"

GEOIP_DIR="${WAF_GEOIP_DIR:-/etc/nginx/geoip}"
GEOIP_MODULE="/usr/local/openresty/nginx/modules/ngx_http_geoip2_module.so"
SNIP_LOAD="/etc/nginx/snippets/geoip2-load.conf"
SNIP_HTTP="/etc/nginx/snippets/geoip2-http.conf"

: >"$SNIP_LOAD"
: >"$SNIP_HTTP"

if [ -f "$GEOIP_MODULE" ] && compgen -G "$GEOIP_DIR/*.mmdb" >/dev/null; then
  startup_sub "GeoIP2 已启用 (${GEOIP_DIR})"
  echo "GeoIP2 enabled: using MaxMind databases from ${GEOIP_DIR}" >&2
  echo "load_module modules/ngx_http_geoip2_module.so;" >"$SNIP_LOAD"
  {
    if [ -f "$GEOIP_DIR/GeoLite2-Country.mmdb" ]; then
      cat <<'NGX'
geoip2 /etc/nginx/geoip/GeoLite2-Country.mmdb {
    auto_reload 60m;
    $geoip2_country source=$waf_geoip_client country iso_code;
}
NGX
    fi
    if [ -f "$GEOIP_DIR/GeoLite2-City.mmdb" ]; then
      cat <<'NGX'
geoip2 /etc/nginx/geoip/GeoLite2-City.mmdb {
    auto_reload 60m;
    $geoip2_region source=$waf_geoip_client subdivisions 0 iso_code;
    $geoip2_city   source=$waf_geoip_client city names en;
}
NGX
    fi
    if [ -f "$GEOIP_DIR/GeoLite2-ASN.mmdb" ]; then
      cat <<'NGX'
geoip2 /etc/nginx/geoip/GeoLite2-ASN.mmdb {
    auto_reload 60m;
    $geoip2_asn source=$waf_geoip_client autonomous_system_number;
    $geoip2_isp source=$waf_geoip_client autonomous_system_organization;
}
NGX
    fi
  } >"$SNIP_HTTP"
elif compgen -G "$GEOIP_DIR/*.mmdb" >/dev/null; then
  echo "WARN: GeoLite2 .mmdb found in ${GEOIP_DIR} but ${GEOIP_MODULE} is missing; geo fields disabled" >&2
fi

cat >/etc/flowshield/env <<EOF
export DB_PATH='${DB_PATH:-/data/waf.db}'
export REDIS_HOST='${REDIS_HOST:-redis}'
export REDIS_PORT='${REDIS_PORT:-6379}'
export REDIS_SOCKET_PATH='${REDIS_SOCKET_PATH:-}'
export REDIS_PASSWORD='${REDIS_PASSWORD}'
export REDIS_POOL_SIZE='${REDIS_POOL_SIZE:-256}'
export REDIS_KEEPALIVE_MS='${REDIS_KEEPALIVE_MS:-60000}'
export JWT_SECRET='${JWT_SECRET}'
export JWT_ACCESS_TTL_MIN='${JWT_ACCESS_TTL_MIN:-120}'
export JWT_REFRESH_TTL_DAYS='${JWT_REFRESH_TTL_DAYS:-3}'
export WAF_CHALLENGE_SECRET='${WAF_CHALLENGE_SECRET}'
export ENABLE_DOCS='${ENABLE_DOCS:-true}'
export CLICKHOUSE_HOST='${CLICKHOUSE_HOST:-clickhouse}'
export CLICKHOUSE_PORT='${CLICKHOUSE_PORT:-8123}'
export CLICKHOUSE_USER='${CLICKHOUSE_USER:-default}'
export CLICKHOUSE_PASSWORD='${CLICKHOUSE_PASSWORD:-}'
export CLICKHOUSE_DATABASE='${CLICKHOUSE_DATABASE:-waf}'
export CLICKHOUSE_ASYNC_INSERT='${CLICKHOUSE_ASYNC_INSERT:-true}'
export CLICKHOUSE_HOURLY_MV_ENABLED='${CLICKHOUSE_HOURLY_MV_ENABLED:-false}'
export LOG_COLLECTOR_BATCH_SIZE='${LOG_COLLECTOR_BATCH_SIZE:-2000}'
export LOG_COLLECTOR_MAX_DRAIN_BATCHES='${LOG_COLLECTOR_MAX_DRAIN_BATCHES:-4}'
export LOG_COLLECTOR_BOT_CATALOG_REFRESH_SEC='${LOG_COLLECTOR_BOT_CATALOG_REFRESH_SEC:-30}'
export LOG_LEVEL='${LOG_LEVEL:-WARNING}'
export ENGINE_CONF_DIR=/data/engine/conf.d
export ENGINE_CERT_DIR=/data/engine/certs
export SLIDE_CAPTCHA_ASSETS_DIR='${SLIDE_CAPTCHA_ASSETS_DIR:-/data/slide_captcha}'
export WAF_BACKEND_URL='unix:/run/flowshield/backend.sock'
EOF

# 首次启动时，若挂载目录为空则写入内置默认素材
if [ ! -d "${SLIDE_CAPTCHA_ASSETS_DIR:-/data/slide_captcha}/tiles" ] || \
   [ -z "$(ls -A "${SLIDE_CAPTCHA_ASSETS_DIR:-/data/slide_captcha}/tiles" 2>/dev/null)" ]; then
  mkdir -p "${SLIDE_CAPTCHA_ASSETS_DIR:-/data/slide_captcha}"
  cp -R /opt/flowshield/slide-captcha-defaults/. "${SLIDE_CAPTCHA_ASSETS_DIR:-/data/slide_captcha}/"
fi

# 集中等待 Redis，避免 backend/worker/engine 各自轮询并刷屏
/opt/flowshield/wait-for.sh

startup_step "3/5" "启动服务进程 (backend / worker / engine / panel)"
exec /usr/bin/supervisord -n -c /etc/supervisor/supervisord.conf
