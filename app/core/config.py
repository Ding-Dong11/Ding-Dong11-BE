from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # CORS — 쉼표로 구분된 허용 origin 목록 (예: http://localhost:5173,https://xxx.trycloudflare.com)
    # pydantic-settings 2.x 는 list[str] 필드를 JSON으로 먼저 파싱해 쉼표 구분이 깨지므로 str로 받아 property에서 분리
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # PostgreSQL
    postgres_user: str = "dingdong"
    postgres_password: str = "dingdong"
    postgres_db: str = "dingdong"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_url: str | None = None

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14

    # 이메일 인증 (database.md Redis 섹션 TTL과 일치)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    email_verify_ttl_seconds: int = 600
    email_verify_cooldown_seconds: int = 180

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-8"

    # 공공데이터 Open API
    data_go_kr_service_key: str = ""
    data_go_kr_stores_api_url: str = ""
    data_go_kr_dispositions_api_url: str = ""
    sgis_consumer_key: str = ""
    sgis_consumer_secret: str = ""

    # 지오코딩
    kakao_rest_api_key: str = ""
    vworld_api_key: str = ""

    # ETL
    etl_http_timeout: float = 30.0
    etl_max_retries: int = 3
    etl_rate_limit_per_sec: float = 5.0
    etl_chunk_size: int = 2000
    etl_stores_csv_path: str = "./data/stores"
    geocode_cache_ttl_seconds: int = 2592000

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_connection_url(self) -> str:
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
