from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _parse_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "on", "yes"}:
        return True
    if lowered in {"0", "false", "off", "no"}:
        return False
    return default


def _parse_int(value: Optional[str], default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


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
    nfse_wsdl_url: Optional[str]
    nfse_service_url: Optional[str]
    nfse_timeout: int
    nfse_verify_ssl: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            secret_key=os.getenv("BPO_SECRET_KEY", "troque-essa-chave"),
            database_url=os.getenv("BPO_DATABASE_URL", "sqlite:///./bpo_finance.db"),
            admin_email=os.getenv("BPO_ADMIN_EMAIL", "admin@bpo.exemplo.com"),
            admin_password=os.getenv("BPO_ADMIN_PASSWORD", "admin123"),
            admin_name=os.getenv("BPO_ADMIN_NAME", "Administrador"),
            nfse_wsdl_url=os.getenv("BPO_NFSE_WSDL_URL"),
            nfse_service_url=os.getenv("BPO_NFSE_SERVICE_URL"),
            nfse_timeout=_parse_int(os.getenv("BPO_NFSE_TIMEOUT"), 30),
            nfse_verify_ssl=_parse_bool(os.getenv("BPO_NFSE_VERIFY_SSL"), True),
        )


_cached_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _cached_settings
    if _cached_settings is None:
        _load_env_file()
        _cached_settings = Settings.from_env()
    return _cached_settings


__all__ = ["Settings", "get_settings"]
