"""Interface de linha de comando para emissão de NFS-e de Goiânia."""

from __future__ import annotations

import argparse
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from ..database import session_scope
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
        return yaml.safe_load(caminho.read_text(encoding="utf-8"))
    return json.loads(caminho.read_text(encoding="utf-8"))


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
    if isinstance(competencia, str):
        ano, mes, dia = competencia.split("-") + ["01"] * (3 - len(competencia.split("-")))
        competencia_date = date(int(ano), int(mes), int(dia))
    elif isinstance(competencia, (list, tuple)):
        competencia_date = date(int(competencia[0]), int(competencia[1]), int(competencia[2]))
    else:
        competencia_date = date.today()

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

    empresa = carregar_empresa(args.empresa)
    payload = carregar_payload(Path(args.input))
    nota = criar_nota(payload)

    cliente = NfseGoianiaClient(
        empresa=empresa,
        senha_certificado=args.senha_cert,
        usuario_portal=args.usuario_portal,
        senha_portal=args.senha_portal,
    )

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
