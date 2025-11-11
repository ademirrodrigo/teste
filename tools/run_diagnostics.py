"""Ferramentas de verificação rápida do ambiente do BPO Financeiro."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from bpo_app import database, main as app_main
from bpo_app.models import Company, User, UserRole
from bpo_app.settings import get_settings


MODULE_CHECKS: Dict[str, str] = {
    "fastapi": "API principal e autenticação",
    "uvicorn": "Servidor ASGI para rodar o backend",
    "sqlalchemy": "Camada de acesso ao banco de dados",
    "pydantic": "Validação e serialização de dados",
    "pandas": "Importação e relatórios financeiros",
    "openpyxl": "Importação de planilhas Excel",
    "ofxparse": "Importação de extratos OFX",
    "reportlab": "Exportação de relatórios em PDF",
    "zeep": "Integração NFSe (SOAP)",
}


@dataclass
class ModuleStatus:
    name: str
    purpose: str


@dataclass
class DiagnosticsResult:
    missing_modules: List[ModuleStatus]
    settings_warnings: List[str]
    database: Dict[str, int]
    assets: Dict[str, bool]


def _check_modules() -> List[ModuleStatus]:
    missing: List[ModuleStatus] = []
    for module_name, purpose in MODULE_CHECKS.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(ModuleStatus(name=module_name, purpose=purpose))
    return missing


def _check_settings() -> List[str]:
    warnings: List[str] = []
    settings = get_settings()
    if settings.secret_key == "troque-essa-chave":
        warnings.append(
            "Defina BPO_SECRET_KEY com um valor seguro para proteger os tokens de acesso."
        )
    if not settings.admin_password_from_env and settings.admin_password == "admin123":
        warnings.append(
            "Defina BPO_ADMIN_PASSWORD com uma senha forte ou altere a senha do administrador."
        )
    if settings.database_url.startswith("sqlite"):
        warnings.append(
            "O banco de dados está em SQLite. Planeje a migração para PostgreSQL antes de produção."
        )
    return warnings


def _check_database() -> Dict[str, int]:
    app_main.on_startup()

    session_factory = database.get_sessionmaker()
    with session_factory() as session:
        user_count = session.query(User).count()
        admin_count = session.query(User).filter(User.role == UserRole.ADMIN).count()
        company_count = session.query(Company).count()
    return {
        "users": user_count,
        "admins": admin_count,
        "companies": company_count,
    }


def _check_assets() -> Dict[str, bool]:
    base_path = Path(__file__).resolve().parent.parent
    frontend_dir = base_path / "bpo_app" / "frontend"
    return {
        "frontend_index": (frontend_dir / "index.html").is_file(),
        "frontend_scripts": (frontend_dir / "main.js").is_file(),
        "frontend_styles": (frontend_dir / "styles.css").is_file(),
        "manual_canva": (base_path / "docs" / "manual_canva.md").is_file(),
        "installers_folder": (base_path / "installers").is_dir(),
    }


def collect_diagnostics() -> DiagnosticsResult:
    return DiagnosticsResult(
        missing_modules=_check_modules(),
        settings_warnings=_check_settings(),
        database=_check_database(),
        assets=_check_assets(),
    )


def run_cli() -> None:
    parser = argparse.ArgumentParser(
        description="Executa verificações rápidas de ambiente e instalação do BPO Financeiro."
    )
    parser.add_argument(
        "--json", action="store_true", help="Retorna a saída em formato JSON compacto"
    )
    args = parser.parse_args()

    result = collect_diagnostics()
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
        return

    if result.missing_modules:
        print("⚠️  Módulos Python ausentes:")
        for item in result.missing_modules:
            print(f"  - {item.name}: {item.purpose}")
    else:
        print("✅ Todas as dependências Python principais estão instaladas.")

    if result.settings_warnings:
        print("\n⚠️  Ajustes recomendados nas configurações:")
        for warning in result.settings_warnings:
            print(f"  - {warning}")
    else:
        print("\n✅ Variáveis de ambiente essenciais configuradas.")

    db_info = result.database
    print(
        f"\n📊 Banco de dados: {db_info['users']} usuário(s), {db_info['admins']} admin(s), {db_info['companies']} empresa(s)."
    )

    print("\n🗂️  Itens de instalação e frontend:")
    for asset, exists in result.assets.items():
        status = "OK" if exists else "Faltando"
        print(f"  - {asset.replace('_', ' ').title()}: {status}")


if __name__ == "__main__":
    run_cli()
