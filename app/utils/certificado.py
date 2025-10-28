"""Rotinas relacionadas a certificados digitais A1."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import settings
from .cnpj import sanitize_cnpj


def get_certificado_path(cnpj: str, arquivo_personalizado: Optional[str] = None) -> Path:
    """Localiza o certificado PFX correspondente ao CNPJ informado."""
    cnpj_limpo = sanitize_cnpj(cnpj)
    if arquivo_personalizado:
        return settings.certs_dir / arquivo_personalizado
    return settings.certs_dir / f"{cnpj_limpo}.pfx"


def carregar_certificado(cnpj: str, senha: str) -> tuple[Path, str]:
    """Retorna metadados do certificado. A carga real via requests_pkcs12 é comentada."""
    certificado = get_certificado_path(cnpj)
    if not certificado.exists():
        raise FileNotFoundError(
            "Certificado não encontrado. Salve o arquivo .pfx na pasta 'certs/'."
        )

    # Exemplo de como carregar o certificado com requests_pkcs12:
    # from requests_pkcs12 import Pkcs12Adapter
    # session = requests.Session()
    # session.mount("https://", Pkcs12Adapter(pkcs12_filename=str(certificado), pkcs12_password=senha))
    # return session

    # O retorno contém o caminho e a senha para ser utilizado quando a integração for ativada.
    return certificado, senha
