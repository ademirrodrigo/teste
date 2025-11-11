from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

ABRASF_NAMESPACE = "http://www.abrasf.org.br/nfse.xsd"
GOIANIA_MUNICIPAL_CODE = "5208707"


def _ensure_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _format_decimal(value: Decimal | float | int | str) -> str:
    dec = _ensure_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{dec:.2f}"


def _only_digits(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return "".join(ch for ch in value if ch.isdigit()) or None


def _serialize(element: Element) -> str:
    xml_bytes = tostring(element, encoding="utf-8", xml_declaration=False)
    return xml_bytes.decode("utf-8")


@dataclass(slots=True)
class GoianiaPrestador:
    cnpj: str
    inscricao_municipal: str


@dataclass(slots=True)
class GoianiaTomadorEndereco:
    logradouro: str
    numero: str
    bairro: str
    codigo_municipio: str = GOIANIA_MUNICIPAL_CODE
    uf: str = "GO"
    cep: Optional[str] = None
    complemento: Optional[str] = None


@dataclass(slots=True)
class GoianiaTomador:
    razao_social: str
    cpf_cnpj: str
    inscricao_municipal: Optional[str]
    email: Optional[str]
    telefone: Optional[str]
    endereco: GoianiaTomadorEndereco


@dataclass(slots=True)
class GoianiaServicoValores:
    valor_servicos: Decimal
    valor_deducoes: Decimal = Decimal("0")
    valor_pis: Decimal = Decimal("0")
    valor_cofins: Decimal = Decimal("0")
    valor_inss: Decimal = Decimal("0")
    valor_ir: Decimal = Decimal("0")
    valor_csll: Decimal = Decimal("0")
    outros_retencoes: Decimal = Decimal("0")
    iss_retido: int = 2
    valor_iss: Optional[Decimal] = None
    valor_iss_retido: Optional[Decimal] = None
    aliquota: Optional[Decimal] = None
    desconto_condicionado: Optional[Decimal] = None
    desconto_incondicionado: Optional[Decimal] = None


@dataclass(slots=True)
class GoianiaServico:
    valores: GoianiaServicoValores
    item_lista_servico: str
    codigo_tributacao_municipio: str
    discriminacao: str
    codigo_municipio: str = GOIANIA_MUNICIPAL_CODE


@dataclass(slots=True)
class GoianiaNfseEmission:
    numero_lote: str
    numero_rps: str
    serie_rps: str
    tipo_rps: int
    data_emissao: datetime
    natureza_operacao: int
    regime_especial_tributacao: Optional[int]
    optante_simples: int
    incentivador_cultural: int
    status_rps: int
    prestador: GoianiaPrestador
    servico: GoianiaServico
    tomador: GoianiaTomador


def build_goiania_header(versao: str = "2.03") -> str:
    root = Element(f"{{{ABRASF_NAMESPACE}}}cabecalho", versao=versao)
    SubElement(root, "VersaoDados").text = versao
    return _serialize(root)


def _append_optional(parent: Element, tag: str, value: Optional[str]) -> None:
    if value is None:
        return
    SubElement(parent, tag).text = value


def _append_decimal(parent: Element, tag: str, value: Optional[Decimal]) -> None:
    if value is None:
        return
    SubElement(parent, tag).text = _format_decimal(value)


def build_goiania_gerar_nfse(emission: GoianiaNfseEmission) -> str:
    root = Element(f"{{{ABRASF_NAMESPACE}}}GerarNfseEnvio")

    lote = SubElement(root, "LoteRps")
    SubElement(lote, "NumeroLote").text = emission.numero_lote
    SubElement(lote, "Cnpj").text = _only_digits(emission.prestador.cnpj) or emission.prestador.cnpj
    SubElement(lote, "InscricaoMunicipal").text = _only_digits(emission.prestador.inscricao_municipal)
    SubElement(lote, "QuantidadeRps").text = "1"

    lista_rps = SubElement(lote, "ListaRps")
    rps = SubElement(lista_rps, "Rps")
    inf_rps = SubElement(rps, "InfRps", Id=f"RPS{emission.numero_rps}")

    identificacao = SubElement(inf_rps, "IdentificacaoRps")
    SubElement(identificacao, "Numero").text = emission.numero_rps
    SubElement(identificacao, "Serie").text = emission.serie_rps
    SubElement(identificacao, "Tipo").text = str(emission.tipo_rps)

    SubElement(inf_rps, "DataEmissao").text = emission.data_emissao.strftime("%Y-%m-%dT%H:%M:%S")
    SubElement(inf_rps, "NaturezaOperacao").text = str(emission.natureza_operacao)
    if emission.regime_especial_tributacao is not None:
        SubElement(inf_rps, "RegimeEspecialTributacao").text = str(emission.regime_especial_tributacao)
    SubElement(inf_rps, "OptanteSimplesNacional").text = str(emission.optante_simples)
    SubElement(inf_rps, "IncentivadorCultural").text = str(emission.incentivador_cultural)
    SubElement(inf_rps, "Status").text = str(emission.status_rps)

    servico = SubElement(inf_rps, "Servico")
    valores = SubElement(servico, "Valores")
    SubElement(valores, "ValorServicos").text = _format_decimal(emission.servico.valores.valor_servicos)
    _append_decimal(valores, "ValorDeducoes", emission.servico.valores.valor_deducoes)
    _append_decimal(valores, "ValorPis", emission.servico.valores.valor_pis)
    _append_decimal(valores, "ValorCofins", emission.servico.valores.valor_cofins)
    _append_decimal(valores, "ValorInss", emission.servico.valores.valor_inss)
    _append_decimal(valores, "ValorIr", emission.servico.valores.valor_ir)
    _append_decimal(valores, "ValorCsll", emission.servico.valores.valor_csll)
    _append_decimal(valores, "OutrasRetencoes", emission.servico.valores.outros_retencoes)
    SubElement(valores, "IssRetido").text = str(emission.servico.valores.iss_retido)
    _append_decimal(valores, "ValorIss", emission.servico.valores.valor_iss)
    _append_decimal(valores, "ValorIssRetido", emission.servico.valores.valor_iss_retido)
    _append_decimal(valores, "Aliquota", emission.servico.valores.aliquota)
    _append_decimal(valores, "DescontoCondicionado", emission.servico.valores.desconto_condicionado)
    _append_decimal(valores, "DescontoIncondicionado", emission.servico.valores.desconto_incondicionado)

    SubElement(servico, "ItemListaServico").text = emission.servico.item_lista_servico
    SubElement(servico, "CodigoTributacaoMunicipio").text = emission.servico.codigo_tributacao_municipio
    SubElement(servico, "Discriminacao").text = emission.servico.discriminacao
    SubElement(servico, "CodigoMunicipio").text = emission.servico.codigo_municipio

    prestador = SubElement(inf_rps, "Prestador")
    SubElement(prestador, "Cnpj").text = _only_digits(emission.prestador.cnpj) or emission.prestador.cnpj
    SubElement(prestador, "InscricaoMunicipal").text = _only_digits(emission.prestador.inscricao_municipal)

    tomador = SubElement(inf_rps, "Tomador")
    identificacao_tomador = SubElement(tomador, "IdentificacaoTomador")
    cpf_cnpj = SubElement(identificacao_tomador, "CpfCnpj")
    digits_tomador = _only_digits(emission.tomador.cpf_cnpj)
    if digits_tomador and len(digits_tomador) == 11:
        SubElement(cpf_cnpj, "Cpf").text = digits_tomador
    else:
        SubElement(cpf_cnpj, "Cnpj").text = digits_tomador or emission.tomador.cpf_cnpj
    _append_optional(identificacao_tomador, "InscricaoMunicipal", _only_digits(emission.tomador.inscricao_municipal))

    SubElement(tomador, "RazaoSocial").text = emission.tomador.razao_social
    endereco = SubElement(tomador, "Endereco")
    SubElement(endereco, "Endereco").text = emission.tomador.endereco.logradouro
    SubElement(endereco, "Numero").text = emission.tomador.endereco.numero
    _append_optional(endereco, "Complemento", emission.tomador.endereco.complemento)
    SubElement(endereco, "Bairro").text = emission.tomador.endereco.bairro
    SubElement(endereco, "CodigoMunicipio").text = emission.tomador.endereco.codigo_municipio
    SubElement(endereco, "Uf").text = emission.tomador.endereco.uf
    _append_optional(endereco, "Cep", _only_digits(emission.tomador.endereco.cep))

    contato = SubElement(tomador, "Contato")
    _append_optional(contato, "Telefone", _only_digits(emission.tomador.telefone))
    _append_optional(contato, "Email", emission.tomador.email)

    return _serialize(root)


def build_goiania_payload(emission: GoianiaNfseEmission, versao: str = "2.03") -> tuple[str, str]:
    cabecalho = build_goiania_header(versao=versao)
    dados = build_goiania_gerar_nfse(emission)
    return cabecalho, dados


__all__ = [
    "ABRASF_NAMESPACE",
    "GoianiaNfseEmission",
    "GoianiaPrestador",
    "GoianiaServico",
    "GoianiaServicoValores",
    "GoianiaTomador",
    "GoianiaTomadorEndereco",
    "build_goiania_payload",
]
