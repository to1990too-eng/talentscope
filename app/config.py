"""Конфигурация приложения на основе pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки, загружаемые из .env и переменных окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Приложение ---
    app_name: str = "TalentScope"
    app_env: Literal["local", "staging", "production"] = "local"
    debug: bool = False
    log_level: str = "INFO"

    # --- PostgreSQL ---
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "talentscope"
    postgres_password: str = "talentscope"
    postgres_db: str = "talentscope"

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # --- Anthropic ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # --- Внешние API ---
    github_token: str | None = None
    arxiv_base_url: str = "http://export.arxiv.org/api/query"
    openalex_base_url: str = "https://api.openalex.org"

    @property
    def database_url(self) -> PostgresDsn:
        """DSN для async SQLAlchemy (asyncpg)."""
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            path=self.postgres_db,
        )

    @property
    def redis_url(self) -> RedisDsn:
        """DSN для redis.asyncio."""
        return RedisDsn.build(
            scheme="redis",
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password or None,
            path=str(self.redis_db),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает кэшированный экземпляр настроек."""
    return Settings()
