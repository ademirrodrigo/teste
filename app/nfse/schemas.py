"""Estruturas de dados para emissão de NFS-e de Goiânia."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class DadosTomador:
    """Informações do tomador do serviço."""

    razao_social: str
    documento: str
    inscricao_municipal: str | None = None
    email: str | None = None
    endereco: str | None = None
    bairro: str | None = None
    cep: str | None = None
    municipio: str | None = None
    uf: str | None = None


@dataclass
class DadosServico:
    """Informações específicas do serviço prestado."""

    codigo_tributacao: str
    aliquota: Decimal
    valor_servico: Decimal
    discriminacao: str
    iss_retido: bool = False
    deducoes: Decimal = Decimal("0")
    codigo_cnae: str | None = None
    codigo_municipio: str | None = None
    codigo_prestador: str | None = None


@dataclass
class NotaServico:
    """Representa uma NFS-e a ser emitida."""

    competencia: date
    tomador: DadosTomador
    servico: DadosServico
    numero_nfse: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    xml_url: Optional[str] = None
    arquivo_salvo: Optional[str] = None
    meta: dict[str, str] = field(default_factory=dict)

    @property
    def competencia_str(self) -> str:
        """Retorna a competência no formato AAAA-MM."""
        return self.competencia.strftime("%Y-%m")
