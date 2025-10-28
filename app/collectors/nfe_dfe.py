"""Coletor responsável por interagir com o WebService NFeDistribuicaoDFe."""

from __future__ import annotations

import base64
import io
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Iterable, List
from zipfile import ZipFile

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Documento, Empresa
from ..utils.certificado import carregar_certificado
from ..utils.helpers import setup_logging

LOGGER = setup_logging()


def _salvar_documento(session: Session, empresa: Empresa, chave: str, xml_conteudo: bytes) -> Documento:
    """Persiste um documento na base de dados e no diretório de XMLs."""
    existente = session.query(Documento).filter_by(chave=chave).one_or_none()
    if existente:
        LOGGER.info("Documento %s já registrado, ignorando duplicata", chave)
        return existente

    destino = empresa.cnpj
    pasta_empresa = settings.xml_dir / destino
    pasta_empresa.mkdir(parents=True, exist_ok=True)

    arquivo_xml = pasta_empresa / f"{chave}.xml"
    arquivo_xml.write_bytes(xml_conteudo)

    try:
        caminho_registrado = str(arquivo_xml.relative_to(settings.base_dir))
    except ValueError:
        caminho_registrado = str(arquivo_xml)

    documento = Documento(
        empresa_id=empresa.id,
        tipo="NFE",
        chave=chave,
        arquivo=caminho_registrado,
        resumo=f"XML coletado em {datetime.utcnow():%Y-%m-%d %H:%M:%S}"
    )
    session.add(documento)
    session.flush()
    LOGGER.info("Documento %s armazenado no banco", chave)
    return documento


def _processar_distdoc(session: Session, empresa: Empresa, documentos: Iterable[ET.Element]) -> List[Documento]:
    """Processa a lista de documentos retornados pelo WebService."""
    resultados: List[Documento] = []
    for doc in documentos:
        namespace_uri = doc.tag.split("}")[0].strip("{") if "}" in doc.tag else ""
        namespaces = {"ns": namespace_uri} if namespace_uri else {}
        caminho = "ns:docZip" if namespace_uri else "docZip"
        doc_zip = doc.findtext(caminho, namespaces=namespaces)
        if not doc_zip:
            continue
        xml_bytes = base64.b64decode(doc_zip)
        with ZipFile(io.BytesIO(xml_bytes)) as zipped:
            for nome in zipped.namelist():
                conteudo = zipped.read(nome)
                chave = nome.replace(".xml", "")
                resultados.append(_salvar_documento(session, empresa, chave, conteudo))
    return resultados


def coletar_nfe_distribuicao(session: Session, empresa: Empresa, nsu_inicial: str | None = None) -> List[Documento]:
    """Executa a consulta no serviço NFeDistribuicaoDFe."""
    LOGGER.info("Iniciando coleta NFeDistribuicaoDFe para %s", empresa.cnpj)

    # As linhas abaixo demonstram como a integração real deve ocorrer.
    certificado, senha = carregar_certificado(empresa.cnpj, empresa.certificado_senha or "")

    # Exemplo comentado de chamada SOAP ao serviço:
    # from zeep import Client
    # from zeep.transports import Transport
    # from requests import Session as HttpSession
    # from requests_pkcs12 import Pkcs12Adapter
    # http_session = HttpSession()
    # http_session.mount(
    #     "https://",
    #     Pkcs12Adapter(pkcs12_filename=str(certificado), pkcs12_password=senha),
    # )
    # transport = Transport(session=http_session, timeout=30)
    # client = Client("https://www.sefazvirtual.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx?wsdl", transport=transport)
    # consulta = {
    #     "distNSU": {
    #         "ultNSU": nsu_inicial or "000000000000000"
    #     }
    # }
    # resposta = client.service.nfeDistDFeInteresse(
    #     cUFAutor=empresa.uf,
    #     tpAmb=1,
    #     CNPJ=empresa.cnpj,
    #     distNSU=consulta["distNSU"],
    # )
    # if hasattr(resposta, "loteDistDFeInt"):
    #     documentos = resposta.loteDistDFeInt.docZip
    #     return _processar_distdoc(session, empresa, documentos)

    # Enquanto a integração real não é ativada, interrompemos aqui.
    LOGGER.warning(
        "Coleta NFeDistribuicaoDFe está preparada, porém a chamada ao WebService permanece comentada por segurança."
    )
    return []
