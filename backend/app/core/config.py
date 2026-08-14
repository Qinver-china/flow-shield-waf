"""Application settings loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database (SQLite embedded config store)
    db_path: str = "/data/waf.db"

    # redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_password: str = ""
    redis_socket_path: str = ""
    redis_max_connections: int = 64

    # auth
    jwt_secret: str = "FlowShield_JWT_ChangeMe_ToYourOwnSecret_32b"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_min: int = 120
    jwt_refresh_ttl_days: int = 3

    # waf
    waf_challenge_secret: str = "FlowShield_Challenge_ChangeMe_Secret32"
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

    # application logging (backend + worker); WARNING = only warnings/errors
    log_level: str = "WARNING"

    # log collector (worker)
    log_collector_batch_size: int = 2000
    log_collector_max_drain_batches: int = 4
    log_collector_bot_catalog_refresh_sec: int = 30

    # vendored Crawler-Detect rules (JayBizzle/Crawler-Detect)
    crawler_vendored_path: str = ""
    crawler_vendored_auto_update_days: int = 30
    crawler_vendored_check_interval_sec: int = 3600

    # engine integration
    engine_conf_dir: str = "/data/engine/conf.d"
    engine_cert_dir: str = "/data/engine/certs"
    engine_reload_url: str = "http://engine/.waf/reload"
    # Loopback health probe (same host as OpenResty in app/baota layouts).
    engine_health_url: str = "http://127.0.0.1/waf-health"
    # Public panel URL for links in emails (no trailing slash).
    # Configured in system settings (waf_setting.panel_public_url).
    # Docker host gateway when origin_host is localhost (container localhost != host).
    waf_origin_host_gateway: str = "172.17.0.1"
    # slide captcha static assets (backgrounds + tiles); Docker 默认 /data/slide_captcha
    slide_captcha_assets_dir: str = ""

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.db_path}"

    @property
    def data_dir(self) -> str:
        import os

        parent = os.path.dirname(self.db_path)
        return parent or "/data"

    @property
    def crawler_vendored_dir(self) -> str:
        if self.crawler_vendored_path.strip():
            return self.crawler_vendored_path.strip()
        import os

        return os.path.join(self.data_dir, "crawler_vendored")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
