"""Utilidades para armazenamento de NFS-e."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..config import settings
from ..utils.helpers import ensure_subdirectories


def gerar_caminho_nfse(cnpj: str, competencia: date, nome_arquivo: str) -> Path:
    """Cria o caminho padronizado empresa/ano/mes para salvar XML da NFS-e."""
    base = settings.nfse_dir / cnpj
    ano = f"{competencia.year:04d}"
    mes = f"{competencia.month:02d}"
    ensure_subdirectories(base, [ano, f"{ano}/{mes}"])
    return base / ano / mes / nome_arquivo
