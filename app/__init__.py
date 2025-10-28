"""Inicialização do pacote principal do Coletor Fiscal v3.2 SaaS-Ready."""

from .config import settings
from .database import Base, engine, init_db


__all__ = ["settings", "init_db", "Base", "engine"]
