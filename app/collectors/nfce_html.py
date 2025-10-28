"""Coletor responsável pela raspagem pública da NFC-e da SEFAZ-GO."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

# from requests import Session as HttpSession  # Ative quando habilitar a raspagem real

from ..config import settings
from ..models import Documento, Empresa
from ..utils.helpers import setup_logging

LOGGER = setup_logging()


def _salvar_html(session: Session, empresa: Empresa, chave: str, html: str) -> Documento:
    """Armazena o HTML coletado e registra o documento."""
    existente = session.query(Documento).filter_by(chave=chave).one_or_none()
    if existente:
        LOGGER.info("NFC-e %s já está cadastrada, reutilizando registro", chave)
        return existente

    pasta_empresa = settings.html_dir / empresa.cnpj
    pasta_empresa.mkdir(parents=True, exist_ok=True)
    arquivo_html = pasta_empresa / f"{chave}.html"
    arquivo_html.write_text(html, encoding="utf-8")

    try:
        caminho_registrado = str(arquivo_html.relative_to(settings.base_dir))
    except ValueError:
        caminho_registrado = str(arquivo_html)

    documento = Documento(
        empresa_id=empresa.id,
        tipo="NFCE",
        chave=chave,
        arquivo=caminho_registrado,
        resumo=f"HTML coletado em {datetime.utcnow():%Y-%m-%d %H:%M:%S}"
    )
    session.add(documento)
    session.flush()
    LOGGER.info("NFC-e %s registrada com sucesso", chave)
    return documento


def coletar_nfce_publica(session: Session, empresa: Empresa, chaves: Iterable[str]) -> List[Documento]:
    """Efetua a raspagem pública da NFC-e a partir de chaves fornecidas."""
    documentos: List[Documento] = []
    for chave in chaves:
        LOGGER.info("Iniciando raspagem pública para NFC-e %s", chave)

        # Modelo de chamada HTTP real (comentado para evitar tráfego durante testes):
        # url = f"https://nfe.sefaz.go.gov.br/nfeweb/sites/nfe/consulta-publica?chave={chave}" 
        # response = requests.get(url, timeout=30)
        # response.raise_for_status()
        # html = response.text

        LOGGER.warning(
            "Raspagem NFC-e preparada; habilite a chamada HTTP comentada para ativar a coleta real."
        )
        html = ""  # O HTML seria atribuído pela resposta real.

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        # Aqui podem ser aplicados tratamentos adicionais ao HTML antes do armazenamento.
        documentos.append(_salvar_html(session, empresa, chave, soup.prettify()))
    return documentos
