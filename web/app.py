"""Aplicativo Streamlit para o Coletor Fiscal v3.2 SaaS-Ready."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

import streamlit as st

# O Streamlit executa este arquivo como "app" dentro da pasta "web". Inserimos o
# diretório raiz do projeto no início do sys.path para garantir que o pacote
# backend ``app`` seja encontrado antes deste módulo homônimo.
PROJETO_RAIZ = Path(__file__).resolve().parents[1]
if str(PROJETO_RAIZ) not in sys.path:
    sys.path.insert(0, str(PROJETO_RAIZ))

# Também removemos a referência conflitante se ela apontar para este arquivo.
if sys.modules.get("app") and getattr(sys.modules["app"], "__file__", None) == __file__:
    del sys.modules["app"]

from app import init_db
from app.config import settings
from app.database import session_scope
from app.models import Empresa
from app.services.coleta import coletar_todos
from app.utils.cnpj import sanitize_cnpj, validate_cnpj
from app.utils.helpers import setup_logging

LOGGER = setup_logging()

USUARIO_PADRAO = os.getenv("WEB_USER", "admin")
SENHA_PADRAO = os.getenv("WEB_PASS", "admin")


def autenticar(usuario: str, senha: str) -> bool:
    """Autentica o usuário utilizando credenciais básicas do ambiente."""
    return usuario == USUARIO_PADRAO and senha == SENHA_PADRAO


def carregar_empresas() -> List[Empresa]:
    with session_scope() as session:
        return session.query(Empresa).order_by(Empresa.nome).all()


def salvar_empresa(nome: str, cnpj: str, uf: str, senha_cert: str | None = None) -> None:
    with session_scope() as session:
        empresa = Empresa(nome=nome, cnpj=cnpj, uf=uf, certificado_senha=senha_cert)
        session.add(empresa)
        session.commit()
        LOGGER.info("Empresa %s cadastrada", nome)


def executar_coletas(empresa: Empresa, chaves_nfce: list[str]) -> dict[str, int]:
    with session_scope() as session:
        empresa_refrescada = session.query(Empresa).filter_by(id=empresa.id).one()
        resultado = coletar_todos(session, empresa_refrescada, chaves_nfce)
        session.commit()
        return resultado


def pagina_login() -> None:
    st.title("Coletor Fiscal v3.2 - Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar(usuario, senha):
            st.session_state["autenticado"] = True
            st.experimental_rerun()
        else:
            st.error("Credenciais inválidas. Verifique usuário e senha.")


def pagina_dashboard() -> None:
    st.sidebar.title("Coletor Fiscal v3.2")
    st.sidebar.write(f"Ambiente: {settings.ambiente.upper()}")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.experimental_rerun()

    st.header("Selecione a empresa para coletar documentos")
    empresas = carregar_empresas()
    if not empresas:
        st.warning("Nenhuma empresa cadastrada. Cadastre abaixo antes de coletar.")

    empresa_nomes = {f"{emp.nome} ({emp.cnpj})": emp for emp in empresas}
    selecionado = st.selectbox("Empresa", options=list(empresa_nomes.keys())) if empresas else None
    empresa_escolhida = empresa_nomes.get(selecionado) if selecionado else None

    with st.expander("Cadastrar nova empresa"):
        with st.form("form_empresa"):
            nome = st.text_input("Nome Fantasia")
            cnpj = st.text_input("CNPJ")
            uf = st.text_input("UF", value="GO", max_chars=2)
            senha_cert = st.text_input("Senha do Certificado", type="password")
            enviar = st.form_submit_button("Salvar Empresa")
            if enviar:
                cnpj_limpo = sanitize_cnpj(cnpj)
                if not validate_cnpj(cnpj_limpo):
                    st.error("CNPJ inválido.")
                else:
                    try:
                        salvar_empresa(nome, cnpj_limpo, uf.upper(), senha_cert)
                        st.success("Empresa cadastrada com sucesso!")
                        st.experimental_rerun()
                    except Exception as exc:
                        st.error(f"Erro ao salvar empresa: {exc}")

    chaves_nfce = st.text_area(
        "Informe as chaves NFC-e (uma por linha)",
        help="As chaves serão utilizadas na raspagem pública da SEFAZ-GO.",
    )
    lista_chaves = [linha.strip() for linha in chaves_nfce.splitlines() if linha.strip()]

    if st.button("🔄 Coletar Agora", disabled=empresa_escolhida is None):
        if not empresa_escolhida:
            st.error("Selecione uma empresa antes de iniciar a coleta.")
        else:
            with st.spinner("Executando coletas seguras..."):
                resultado = executar_coletas(empresa_escolhida, lista_chaves)
            st.success(
                f"Coletas finalizadas! NFe: {resultado['nfe']} | NFC-e: {resultado['nfce']}"
            )
            st.info(
                "As integrações com SEFAZ estão prontas e basta remover os comentários indicados no código para ativá-las."
            )


init_db()
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    pagina_login()
else:
    pagina_dashboard()
