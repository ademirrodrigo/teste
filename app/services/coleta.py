"""Serviços de orquestração das rotinas de coleta."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.orm import Session

from ..collectors.nfce_html import coletar_nfce_publica
from ..collectors.nfe_dfe import coletar_nfe_distribuicao
from ..models import Empresa
from ..utils.helpers import setup_logging

LOGGER = setup_logging()


def coletar_todos(session: Session, empresa: Empresa, chaves_nfce: Iterable[str] | None = None) -> dict[str, int]:
    """Executa todas as coletas disponíveis para a empresa informada."""
    resultados = {"nfe": 0, "nfce": 0}

    documentos_nfe = coletar_nfe_distribuicao(session, empresa)
    resultados["nfe"] = len(documentos_nfe)

    if chaves_nfce:
        documentos_nfce = coletar_nfce_publica(session, empresa, chaves_nfce)
        resultados["nfce"] = len(documentos_nfce)

    LOGGER.info(
        "Coletas concluídas para %s | NFe: %s | NFC-e: %s",
        empresa.cnpj,
        resultados["nfe"],
        resultados["nfce"],
    )
    return resultados
