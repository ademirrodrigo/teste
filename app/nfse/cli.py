"""Interface de linha de comando para emissão de NFS-e de Goiânia."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from ..database import init_db, session_scope
from ..models import Empresa
from ..utils.cnpj import sanitize_cnpj
from ..utils.helpers import setup_logging
from .goiania import NfseException, NfseGoianiaClient
from .schemas import DadosServico, DadosTomador, NotaServico

LOGGER = setup_logging()


def carregar_empresa(cnpj: str) -> Empresa:
    cnpj_limpo = sanitize_cnpj(cnpj)
    with session_scope() as session:
        empresa = session.query(Empresa).filter_by(cnpj=cnpj_limpo).one_or_none()
        if not empresa:
            raise SystemExit(f"Empresa {cnpj_limpo} não encontrada. Cadastre-a pelo painel.")
        session.expunge(empresa)
    return empresa


def carregar_payload(caminho: Path) -> dict[str, Any]:
    if not caminho.exists():
        raise SystemExit(f"Arquivo de entrada {caminho} não encontrado.")

    if caminho.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    else:
        payload = json.loads(caminho.read_text(encoding="utf-8"))

    if not payload:
        raise SystemExit(f"O arquivo {caminho} está vazio ou inválido.")

    return payload


def validar_payload(payload: dict[str, Any]) -> None:
    """Valida campos obrigatórios do payload da NFS-e com mensagens claras."""

    def exige_dict(chave: str) -> dict[str, Any]:
        bloco = payload.get(chave)
        if not isinstance(bloco, dict):
            raise ValueError(f"A seção '{chave}' deve ser um objeto com os campos necessários.")
        return bloco

    tomador = exige_dict("tomador")
    servico = exige_dict("servico")

    obrigatorios_tomador = ["razao_social", "documento"]
    obrigatorios_servico = ["codigo_tributacao", "valor_servico", "discriminacao"]

    for campo in obrigatorios_tomador:
        if not tomador.get(campo):
            raise ValueError(f"Campo obrigatório ausente em tomador: '{campo}'.")

    for campo in obrigatorios_servico:
        if servico.get(campo) in (None, ""):
            raise ValueError(f"Campo obrigatório ausente em servico: '{campo}'.")

    if "competencia" in payload:
        competencia = payload["competencia"]
        if not isinstance(competencia, (str, list, tuple)):
            raise ValueError("Competência deve ser string 'AAAA-MM' ou sequência [AAAA, MM, DD].")


def criar_nota(payload: dict[str, Any]) -> NotaServico:
    tomador = payload.get("tomador", {})
    servico = payload.get("servico", {})

    dados_tomador = DadosTomador(
        razao_social=tomador["razao_social"],
        documento=sanitize_cnpj(tomador["documento"]),
        inscricao_municipal=tomador.get("inscricao_municipal"),
        email=tomador.get("email"),
        endereco=tomador.get("endereco"),
        bairro=tomador.get("bairro"),
        cep=tomador.get("cep"),
        municipio=tomador.get("municipio"),
        uf=tomador.get("uf"),
    )

    dados_servico = DadosServico(
        codigo_tributacao=str(servico["codigo_tributacao"]),
        aliquota=Decimal(str(servico.get("aliquota", "0"))),
        valor_servico=Decimal(str(servico["valor_servico"])),
        discriminacao=servico["discriminacao"],
        iss_retido=bool(servico.get("iss_retido", False)),
        deducoes=Decimal(str(servico.get("deducoes", "0"))),
        codigo_cnae=servico.get("codigo_cnae"),
        codigo_municipio=servico.get("codigo_municipio"),
        codigo_prestador=servico.get("codigo_prestador"),
    )

    competencia = payload.get("competencia")

    try:
        if isinstance(competencia, str):
            partes = competencia.split("-")
            while len(partes) < 3:
                partes.append("01")
            ano, mes, dia = (int(v) for v in partes[:3])
            competencia_date = date(ano, mes, dia)
        elif isinstance(competencia, (list, tuple)):
            partes_seq = list(competencia)
            while len(partes_seq) < 3:
                partes_seq.append(1)
            ano, mes, dia = (int(v) for v in partes_seq[:3])
            competencia_date = date(ano, mes, dia)
        else:
            competencia_date = date.today()
    except Exception as exc:
        raise ValueError(f"Competência inválida: {competencia}") from exc

    return NotaServico(
        competencia=competencia_date,
        tomador=dados_tomador,
        servico=dados_servico,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Emissor de NFS-e Goiânia - ISSNet Online")
    parser.add_argument("--empresa", required=True, help="CNPJ da empresa emissora cadastrada")
    parser.add_argument("--senha-cert", required=True, help="Senha do certificado PFX")
    parser.add_argument("--input", required=True, help="Arquivo YAML/JSON com dados da nota")
    parser.add_argument("--usuario-portal", help="Usuário do portal ISSNet (opcional)")
    parser.add_argument("--senha-portal", help="Senha do portal ISSNet (opcional)")
    parser.add_argument("--salvar-json", action="store_true", help="Salvar resumo JSON junto ao XML")

    args = parser.parse_args()

    init_db()

    try:
        empresa = carregar_empresa(args.empresa)
    except Exception as exc:
        LOGGER.error("Erro ao carregar empresa: %s", exc)
        raise SystemExit(1) from exc

    try:
        payload = carregar_payload(Path(args.input))
        validar_payload(payload)
        nota = criar_nota(payload)
    except ValueError as exc:
        LOGGER.error(str(exc))
        raise SystemExit(1) from exc
    except Exception as exc:
        LOGGER.error("Erro ao ler o payload: %s", exc)
        raise SystemExit(1) from exc

    try:
        cliente = NfseGoianiaClient(
            empresa=empresa,
            senha_certificado=args.senha_cert,
            usuario_portal=args.usuario_portal,
            senha_portal=args.senha_portal,
        )
    except FileNotFoundError as exc:
        LOGGER.error("Certificado não encontrado: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:
        LOGGER.error("Erro ao preparar o cliente NFS-e: %s", exc)
        raise SystemExit(1) from exc

    try:
        if args.salvar_json:
            cliente.emitir_e_salvar_json(nota)
        else:
            cliente.emitir_nfse(nota)
    except NfseException as exc:
        LOGGER.error("Erro ao emitir NFS-e: %s", exc)
        raise SystemExit(1) from exc

    LOGGER.info(
        "NFS-e emitida com sucesso | Número: %s | XML: %s",
        nota.numero_nfse,
        nota.arquivo_salvo,
    )


if __name__ == "__main__":
    main()
