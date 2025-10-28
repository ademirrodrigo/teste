"""Inicialização do pacote principal do Coletor Fiscal v3.2 SaaS-Ready."""

from .config import settings
from .database import Base, engine


def init_db() -> None:
    """Cria as tabelas no banco de dados caso ainda não existam."""
    Base.metadata.create_all(bind=engine)


__all__ = ["settings", "init_db", "Base", "engine"]
