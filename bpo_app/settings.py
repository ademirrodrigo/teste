from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _load_env_file() -> None:
    """Populate environment variables from a local .env file if present."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


@dataclass(slots=True)
class Settings:
    secret_key: str
    database_url: str
    admin_email: str
    admin_password: str
    admin_name: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.getenv("BPO_SECRET_KEY", "troque-essa-chave"),
            database_url=os.getenv("BPO_DATABASE_URL", "sqlite:///./bpo_finance.db"),
            admin_email=os.getenv("BPO_ADMIN_EMAIL", "admin@bpo.exemplo.com"),
            admin_password=os.getenv("BPO_ADMIN_PASSWORD", "admin123"),
            admin_name=os.getenv("BPO_ADMIN_NAME", "Administrador"),
        )


_cached_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _cached_settings
    if _cached_settings is None:
        _load_env_file()
        _cached_settings = Settings.from_env()
    return _cached_settings


__all__ = ["Settings", "get_settings"]
