from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LEDGERMIND_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./data/ledgermind.db"

    data_dir: Path = Path("./data")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class InfraSettings(BaseSettings):
    """Infrastructure settings — separate from LEDGERMIND_* prefix."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_mode: str = "server"  # "server" | "memory"

    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str = "ledgermind"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False

    embedding_model: str = Field(default="BAAI/bge-m3")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s


@lru_cache(maxsize=1)
def get_infra() -> InfraSettings:
    return InfraSettings()
