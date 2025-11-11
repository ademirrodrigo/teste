from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

from requests import Session
from zeep import Client, Settings as ZeepSettings
from zeep.exceptions import Fault
from zeep.transports import Transport

NFSE_NAMESPACE = "{http://nfse.abrasf.org.br}nfseSOAP"

ALLOWED_OPERATIONS = {
    "CancelarNfse",
    "ConsultarLoteRps",
    "ConsultarNfseServicoPrestado",
    "ConsultarNfseServicoTomado",
    "ConsultarNfsePorFaixa",
    "ConsultarNfsePorRps",
    "RecepcionarLoteRps",
    "GerarNfse",
    "SubstituirNfse",
    "RecepcionarLoteRpsSincrono",
    "ConsultarUrlNfse",
    "ConsultarDadosCadastrais",
    "ConsultarRpsDisponivel",
}


class NFSeError(Exception):
    """Base error for NFSe integration."""


class NFSeConfigurationError(NFSeError):
    """Raised when the NFSe client is not properly configured."""


class NFSeOperationError(NFSeError):
    """Raised when an invalid request is made to the NFSe service."""


class NFSeServiceError(NFSeError):
    """Raised when the remote NFSe service returns an error."""


@dataclass(eq=True)
class NFSeClientConfig:
    wsdl_url: str
    service_url: Optional[str] = None
    timeout: int = 30
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        self.wsdl_url = self.wsdl_url.strip()
        if not self.wsdl_url:
            raise ValueError("O endereço WSDL do serviço NFSe é obrigatório.")
        if self.service_url:
            cleaned = self.service_url.strip()
            if cleaned:
                self.service_url = _normalize_address(self.wsdl_url, cleaned)
            else:
                self.service_url = None
        if self.timeout <= 0:
            self.timeout = 30


class NFSeClient:
    def __init__(self, config: NFSeClientConfig):
        self.config = config
        self._client: Optional[Client] = None

    def _create_transport(self) -> Transport:
        session = Session()
        session.verify = self.config.verify_ssl
        return Transport(session=session, timeout=self.config.timeout)

    def _get_client(self) -> Client:
        if self._client is None:
            transport = self._create_transport()
            zeep_settings = ZeepSettings(strict=False, xml_huge_tree=True)
            self._client = Client(self.config.wsdl_url, transport=transport, settings=zeep_settings)
        return self._client

    def _get_service(self):
        client = self._get_client()
        address = self.config.service_url or client.service._binding_options.get("address")
        normalized = _normalize_address(self.config.wsdl_url, address)
        return client.create_service(NFSE_NAMESPACE, normalized)

    async def call_operation(self, operation: str, cabec_msg: str, dados_msg: str) -> str:
        op_name = (operation or "").strip()
        if op_name not in ALLOWED_OPERATIONS:
            raise NFSeOperationError(f"Operação NFSe desconhecida: {operation}")

        cabec = (cabec_msg or "").strip()
        dados = (dados_msg or "").strip()
        if not cabec or not dados:
            raise NFSeOperationError("As mensagens nfseCabecMsg e nfseDadosMsg são obrigatórias.")

        service = self._get_service()
        method = getattr(service, op_name, None)
        if method is None:
            raise NFSeOperationError(f"Operação NFSe não suportada pelo serviço: {operation}")

        try:
            response = await asyncio.to_thread(
                method,
                nfseCabecMsg=cabec,
                nfseDadosMsg=dados,
            )
        except Fault as exc:
            raise NFSeServiceError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - proteção adicional
            raise NFSeServiceError("Falha ao comunicar com o serviço NFSe.") from exc

        return _extract_output_xml(response)


def _extract_output_xml(response: object) -> str:
    if response is None:
        return ""
    if isinstance(response, dict):
        value = response.get("outputXML") or response.get("OutputXML")
        if value is not None:
            return str(value)
    output = getattr(response, "outputXML", None) or getattr(response, "OutputXML", None)
    if output is not None:
        return str(output)
    return str(response)


def _normalize_address(wsdl_url: str, address: Optional[str]) -> str:
    if not address:
        raise NFSeConfigurationError("Endereço do serviço NFSe não foi informado no WSDL.")
    cleaned = address.strip()
    if not cleaned:
        raise NFSeConfigurationError("Endereço do serviço NFSe não foi informado no WSDL.")
    parsed = urlparse(cleaned)
    if parsed.scheme:
        return cleaned
    return urljoin(wsdl_url, cleaned)


__all__ = [
    "ALLOWED_OPERATIONS",
    "NFSE_NAMESPACE",
    "NFSeClient",
    "NFSeClientConfig",
    "NFSeConfigurationError",
    "NFSeOperationError",
    "NFSeServiceError",
]
