"""Application settings loaded from environment variables."""
from __future__ import annotations

import sys
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_SECRETS = frozenset({
    "change_me",
    "please_change_this_to_a_long_random_secret",
})
_INSECURE_CHALLENGE_SECRETS = frozenset({
    "change_me_challenge",
    "please_change_this_challenge_secret",
    "waf_default_secret",
})
_INSECURE_ADMIN_PASSWORDS = frozenset({"admin888"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database
    db_host: str = "mysql"
    db_port: int = 3306
    db_name: str = "waf"
    db_user: str = "waf"
    db_password: str = "waf"

    # redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_socket_path: str = ""
    redis_max_connections: int = 64

    # auth
    jwt_secret: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 120
    jwt_refresh_ttl_days: int = 7

    # bootstrap admin
    waf_admin_user: str = "admin"
    waf_admin_password: str = "admin888"

    # waf
    waf_challenge_secret: str = "change_me_challenge"
    waf_allow_insecure_defaults: bool = False
    enable_docs: bool = True
    cors_origins: str = "*"

    # clickhouse
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "waf"
    # Log ingest: larger batches + server-side async_insert reduce insert/MV overhead.
    clickhouse_async_insert: bool = True
    # Hourly MV is unused by queries today; detach on ingest hot path when false.
    clickhouse_hourly_mv_enabled: bool = False

    # log collector (worker)
    log_collector_batch_size: int = 2000
    log_collector_max_drain_batches: int = 4
    log_collector_bot_catalog_refresh_sec: int = 30

    # engine integration
    engine_conf_dir: str = "/data/engine/conf.d"
    engine_cert_dir: str = "/data/engine/certs"
    engine_reload_url: str = "http://engine/.waf/reload"
    # Docker host gateway when origin_host is localhost (container localhost != host).
    waf_origin_host_gateway: str = "172.17.0.1"
    # slide captcha static assets (backgrounds + tiles); Docker 默认 /data/slide_captcha
    slide_captcha_assets_dir: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_socket_path:
            auth = f":{self.redis_password}@" if self.redis_password else ""
            return f"redis://{auth}/0"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "").strip()
        if not raw or raw == "*":
            return ["*"]
        return [part.strip() for part in raw.split(",") if part.strip()]

    def validate_production_secrets(self) -> None:
        if self.waf_allow_insecure_defaults:
            return
        problems: list[str] = []
        if self.jwt_secret in _INSECURE_JWT_SECRETS or len(self.jwt_secret) < 16:
            problems.append("JWT_SECRET 仍为默认值或过短，请设置至少 16 位的随机串")
        if self.waf_challenge_secret in _INSECURE_CHALLENGE_SECRETS or len(self.waf_challenge_secret) < 16:
            problems.append("WAF_CHALLENGE_SECRET 仍为默认值或过短，请设置至少 16 位的随机串")
        if self.waf_admin_password in _INSECURE_ADMIN_PASSWORDS:
            problems.append("WAF_ADMIN_PASSWORD 仍为默认值 admin888，请修改")
        if problems:
            msg = "启动被拒绝：检测到不安全默认配置。\n" + "\n".join(f"  - {p}" for p in problems)
            msg += "\n开发环境可设置 WAF_ALLOW_INSECURE_DEFAULTS=true 临时放行。"
            print(msg, file=sys.stderr)
            raise SystemExit(1)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
