"""Configurações principais do Coletor Fiscal."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    # Permite carregamento alternativo via variáveis de ambiente do sistema.
    load_dotenv()


@dataclass
class Settings:
    """Agrupa as configurações carregadas do ambiente."""

    base_dir: Path = BASE_DIR
    database_url: str = os.getenv("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'data' / os.getenv('BANCO', 'coletor.db')}"
    porta: int = int(os.getenv("PORTA", "8501"))
    ambiente: str = os.getenv("AMBIENTE", "dev")
    secret_key: str = os.getenv("SECRET_KEY", "troque-esta-chave")
    log_dir: Path = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
    xml_dir: Path = Path(os.getenv("XML_DIR", BASE_DIR / "data" / "xmls"))
    html_dir: Path = Path(os.getenv("HTML_DIR", BASE_DIR / "data" / "html"))
    certs_dir: Path = Path(os.getenv("CERTS_DIR", BASE_DIR / "certs"))

    def ensure_directories(self) -> None:
        """Garante a existência dos diretórios necessários."""
        for path in (self.log_dir, self.xml_dir, self.html_dir, self.certs_dir):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
