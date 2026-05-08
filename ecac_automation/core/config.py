from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ecac-automation"
    env: str = "dev"

    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/ecac"
    redis_url: str = "redis://redis:6379/0"

    playwright_headless: bool = True
    session_ttl_seconds: int = 1800

    cert_storage_path: str = "/app/certs"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ECAC_")


@lru_cache
def get_settings() -> Settings:
    return Settings()
