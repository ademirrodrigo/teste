"""Cliente de emissão de NFS-e para a Prefeitura de Goiânia (ISSNet Online)."""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import requests
from bs4 import BeautifulSoup
from requests_pkcs12 import Pkcs12Adapter
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models import Empresa
from ..utils.certificado import carregar_certificado
from ..utils.helpers import setup_logging
from .schemas import NotaServico
from .storage import gerar_caminho_nfse

LOGGER = setup_logging()


class NfseException(RuntimeError):
    """Erro genérico durante a emissão ou download da NFS-e."""


@dataclass
class IssnetEndpoints:
    """Coleção de URLs utilizadas pelo portal ISSNet Online de Goiânia."""

    base_url: str = "https://issonline.goiania.go.gov.br/issnetonline"
    login_path: str = "/Account/Login"
    emissao_path: str = "/Nfse/Emissao"
    download_path: str = "/Nfse/DownloadXml"
    captcha_path: str = "/Account/Captcha"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    @property
    def login_url(self) -> str:
        return f"{self.base_url}{self.login_path}"

    @property
    def emissao_url(self) -> str:
        return f"{self.base_url}{self.emissao_path}"

    @property
    def download_url(self) -> str:
        return f"{self.base_url}{self.download_path}"

    @property
    def captcha_url(self) -> str:
        return f"{self.base_url}{self.captcha_path}"


class CaptchaSolver:
    """Resolve captchas simples do portal (imagem estática)."""

    def __init__(self) -> None:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # noqa: F401

            self._ocr = pytesseract
        except Exception:  # pragma: no cover - usado apenas se disponível
            self._ocr = None

    def solve(self, image_bytes: bytes, manual_callback: Optional[Callable[[bytes], str]] = None) -> str:
        """Tenta resolver via OCR e, se falhar, utiliza entrada manual."""
        if self._ocr:
            try:
                from PIL import Image

                text = self._ocr.image_to_string(Image.open(io.BytesIO(image_bytes)), config="--psm 7")
                cleaned = re.sub(r"\W+", "", text).strip()
                if cleaned:
                    return cleaned
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Falha no OCR do captcha: %s", exc)

        if manual_callback:
            return manual_callback(image_bytes)
        raise NfseException("Não foi possível resolver o captcha automaticamente. Forneça um callback manual.")


class NfseGoianiaClient:
    """Cliente de alto nível para emissão e download de NFS-e no ISSNet Online."""

    def __init__(
        self,
        empresa: Empresa,
        senha_certificado: str,
        usuario_portal: Optional[str] = None,
        senha_portal: Optional[str] = None,
        endpoints: Optional[IssnetEndpoints] = None,
        captcha_solver: Optional[CaptchaSolver] = None,
    ) -> None:
        self.empresa = empresa
        self.senha_certificado = senha_certificado
        self.usuario_portal = usuario_portal or empresa.cnpj
        self.senha_portal = senha_portal or senha_certificado
        self.endpoints = endpoints or IssnetEndpoints()
        self._captcha_solver = captcha_solver or CaptchaSolver()
        self._session = self._criar_sessao()

    def _criar_sessao(self) -> requests.Session:
        certificado, senha = carregar_certificado(self.empresa.cnpj, self.senha_certificado)
        session = requests.Session()
        session.mount("https://", Pkcs12Adapter(pkcs12_filename=str(certificado), pkcs12_password=senha))
        session.headers.update({
            "User-Agent": "Coletor-Fiscal-NFSe/1.0",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        return session

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _get(self, url: str) -> requests.Response:
        resp = self._session.get(url, timeout=30)
        resp.raise_for_status()
        return resp

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
    def _post(self, url: str, data: dict[str, str]) -> requests.Response:
        resp = self._session.post(url, data=data, timeout=30)
        resp.raise_for_status()
        return resp

    def _resolver_captcha(self) -> str:
        resp = self._get(self.endpoints.captcha_url)
        return self._captcha_solver.solve(resp.content, manual_callback=self._manual_captcha)

    def _manual_captcha(self, image_bytes: bytes) -> str:
        destino = settings.log_dir / f"captcha-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
        destino.write_bytes(image_bytes)
        LOGGER.warning(
            "Captcha salvo em %s. Informe o texto manualmente para continuar.", destino
        )
        return input("Captcha exibido no arquivo salvo: ").strip()

    def _extrair_hidden_inputs(self, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "lxml")
        data: dict[str, str] = {}
        for hidden in soup.select("input[type='hidden']"):
            if hidden.get("name"):
                data[hidden["name"]] = hidden.get("value", "")
        return data

    def login(self) -> None:
        LOGGER.info("Abrindo página de login do ISSNet Online para %s", self.empresa.cnpj)
        resp = self._get(self.endpoints.login_url)
        payload = self._extrair_hidden_inputs(resp.text)
        captcha_codigo = self._resolver_captcha()

        form_soup = BeautifulSoup(resp.text, "lxml")
        usuario_field = None
        senha_field = None
        captcha_field = None
        for inp in form_soup.select("input"):
            name = inp.get("name", "").lower()
            if not usuario_field and ("cnpj" in name or "usuario" in name or "login" in name):
                usuario_field = inp.get("name")
            if not senha_field and ("senha" in name or "password" in name):
                senha_field = inp.get("name")
            if not captcha_field and "captcha" in name:
                captcha_field = inp.get("name")

        if not usuario_field or not senha_field:
            raise NfseException("Campos de usuário/senha não encontrados no formulário de login.")

        payload.update({
            usuario_field: self.usuario_portal,
            senha_field: self.senha_portal,
        })
        if captcha_field:
            payload[captcha_field] = captcha_codigo

        resp_login = self._post(self.endpoints.login_url, payload)
        if "NFS-e" not in resp_login.text and resp_login.url.endswith("Login"):
            raise NfseException("Login não autorizado no ISSNet Online.")
        LOGGER.info("Login realizado com sucesso para %s", self.empresa.nome)

    def _montar_payload_emissao(self, nota: NotaServico, html: str) -> dict[str, str]:
        soup = BeautifulSoup(html, "lxml")
        payload = self._extrair_hidden_inputs(html)

        campos = {
            "valor": ["txtValorServico", "valorServico", "ValorServico"],
            "discriminacao": ["txtDiscriminacao", "Discriminacao"],
            "codigo_tributacao": ["txtCodTributacao", "CodigoServico"],
            "aliquota": ["txtAliquota", "Aliquota"],
            "documento_tomador": ["txtCpfCnpjTomador", "DocumentoTomador"],
            "razao_tomador": ["txtRazaoSocialTomador", "RazaoSocialTomador"],
            "email_tomador": ["txtEmailTomador", "EmailTomador"],
            "inscricao_municipal": ["txtInscMunicipalTomador", "InscricaoMunicipalTomador"],
        }

        def set_first(names: list[str], value: str | None) -> None:
            if value is None:
                return
            for name in names:
                if soup.find("input", {"name": name}) or soup.find("textarea", {"name": name}):
                    payload[name] = value
                    return

        set_first(campos["valor"], str(nota.servico.valor_servico))
        set_first(campos["discriminacao"], nota.servico.discriminacao)
        set_first(campos["codigo_tributacao"], nota.servico.codigo_tributacao)
        set_first(campos["aliquota"], str(nota.servico.aliquota))
        set_first(campos["documento_tomador"], nota.tomador.documento)
        set_first(campos["razao_tomador"], nota.tomador.razao_social)
        set_first(campos["email_tomador"], nota.tomador.email)
        set_first(campos["inscricao_municipal"], nota.tomador.inscricao_municipal or "")

        if nota.servico.iss_retido:
            for field in ("chkIssRetido", "IssRetido"):
                if soup.find("input", {"name": field}):
                    payload[field] = "on"

        if nota.servico.deducoes:
            for field in ("txtDeducoes", "ValorDeducoes"):
                if soup.find("input", {"name": field}):
                    payload[field] = str(nota.servico.deducoes)

        return payload

    def emitir_nfse(self, nota: NotaServico, salvar_xml: bool = True) -> NotaServico:
        try:
            self.login()
        except RetryError as exc:  # pragma: no cover - exceção de rede
            raise NfseException(f"Falha ao autenticar no ISSNet Online: {exc}") from exc

        LOGGER.info("Acessando formulário de emissão de NFS-e")
        resp_form = self._get(self.endpoints.emissao_url)
        payload = self._montar_payload_emissao(nota, resp_form.text)

        LOGGER.info("Enviando dados da NFS-e para emissão")
        resp_emitir = self._post(self.endpoints.emissao_url, payload)
        texto_retorno = resp_emitir.text

        numero = self._buscar_regex(texto_retorno, r"NFSe\s*:?\s*(\d+)")
        codigo = self._buscar_regex(texto_retorno, r"C[oó]digo de Verifica[cç][aã]o\s*:?\s*([A-Za-z0-9-]+)")
        xml_link = self._extrair_link_xml(resp_emitir.text)

        if not numero:
            raise NfseException("O portal não retornou o número da NFS-e. Verifique os dados enviados e o layout atual.")

        nota.numero_nfse = numero
        nota.codigo_verificacao = codigo
        nota.xml_url = xml_link
        LOGGER.info("NFS-e %s emitida com sucesso", numero)

        if salvar_xml:
            self.baixar_xml(nota)
        return nota

    def _buscar_regex(self, texto: str, pattern: str) -> Optional[str]:
        encontrado = re.search(pattern, texto, flags=re.IGNORECASE)
        return encontrado.group(1).strip() if encontrado else None

    def _extrair_link_xml(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "lxml")
        for link in soup.find_all("a"):
            href = link.get("href", "")
            if "xml" in href.lower():
                if href.startswith("http"):
                    return href
                return f"{self.endpoints.base_url}{href}"
        return None

    def baixar_xml(self, nota: NotaServico) -> str:
        if nota.xml_url:
            resp = self._get(nota.xml_url)
        else:
            if not nota.numero_nfse:
                raise NfseException("Número da NFS-e ausente; não é possível baixar o XML.")
            params = {"numero": nota.numero_nfse, "competencia": nota.competencia.strftime("%Y-%m")}
            resp = self._post(self.endpoints.download_url, data=params)

        nome_arquivo = f"NFSe-{nota.numero_nfse}-{nota.competencia.strftime('%Y%m')}.xml"
        destino = gerar_caminho_nfse(self.empresa.cnpj, nota.competencia, nome_arquivo)
        destino.write_bytes(resp.content)
        nota.arquivo_salvo = str(destino)
        LOGGER.info("XML da NFS-e salvo em %s", destino)
        return str(destino)

    def emitir_e_salvar_json(self, nota: NotaServico, destino_json: Optional[str] = None) -> str:
        """Emite a nota e salva um espelho em JSON junto ao XML."""
        nota_emitida = self.emitir_nfse(nota, salvar_xml=True)
        destino_json = destino_json or nota_emitida.arquivo_salvo.replace(".xml", ".json")
        payload = {
            "numero": nota_emitida.numero_nfse,
            "codigo_verificacao": nota_emitida.codigo_verificacao,
            "competencia": nota_emitida.competencia.isoformat(),
            "tomador": nota_emitida.tomador.__dict__,
            "servico": {
                "codigo_tributacao": nota_emitida.servico.codigo_tributacao,
                "aliquota": str(nota_emitida.servico.aliquota),
                "valor_servico": str(nota_emitida.servico.valor_servico),
                "discriminacao": nota_emitida.servico.discriminacao,
                "iss_retido": nota_emitida.servico.iss_retido,
                "deducoes": str(nota_emitida.servico.deducoes),
            },
            "arquivo_xml": nota_emitida.arquivo_salvo,
        }
        Path(destino_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        LOGGER.info("Resumo da NFS-e salvo em %s", destino_json)
        return destino_json


__all__ = [
    "NfseGoianiaClient",
    "IssnetEndpoints",
    "NfseException",
]
