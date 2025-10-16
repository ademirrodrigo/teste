"""Instalador unificado para preparar o ambiente do monitor eCAC.

Este script cobre Windows (execução local) e Linux (incluindo VPS) de forma
idêntica, automatizando a criação de ambiente virtual, instalação das
dependências e preparação dos arquivos de configuração padrão.
"""

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List
import venv

ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / ".venv"
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
MONITOR_CONFIG_TEMPLATE = ROOT_DIR / "monitor_config.example.json"
API_CONFIG_TEMPLATE = ROOT_DIR / "api_config.example.json"
MONITOR_CONFIG_TARGET = ROOT_DIR / "monitor_config.json"
API_CONFIG_TARGET = ROOT_DIR / "api_config.json"


class Installer:
    """Responsável por orquestrar as etapas da instalação."""

    def __init__(self) -> None:
        self.system = platform.system().lower()

    def run(self) -> None:
        self._ensure_python_version()
        self._create_virtualenv()
        self._install_dependencies()
        self._prepare_configs()
        self._print_success_message()

    def _ensure_python_version(self) -> None:
        if sys.version_info < (3, 9):
            raise SystemExit(
                "Python 3.9 ou superior é obrigatório. Atualize a instalação antes de continuar."
            )

    def _create_virtualenv(self) -> None:
        if VENV_DIR.exists():
            print(f"Ambiente virtual já existe em {VENV_DIR}. Pulando criação.")
            return
        print(f"Criando ambiente virtual em {VENV_DIR}...")
        builder = venv.EnvBuilder(with_pip=True, upgrade=False, clear=False)
        builder.create(VENV_DIR)

    def _install_dependencies(self) -> None:
        if not REQUIREMENTS_FILE.exists():
            raise SystemExit("Arquivo requirements.txt não encontrado.")
        print("Instalando dependências no ambiente virtual...")
        python_executable = self._venv_python()
        upgrade_cmd = [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"]
        self._run_command(upgrade_cmd)
        install_cmd = [
            str(python_executable),
            "-m",
            "pip",
            "install",
            "-r",
            str(REQUIREMENTS_FILE),
        ]
        self._run_command(install_cmd)

    def _prepare_configs(self) -> None:
        self._copy_if_missing(MONITOR_CONFIG_TEMPLATE, MONITOR_CONFIG_TARGET)
        self._copy_if_missing(API_CONFIG_TEMPLATE, API_CONFIG_TARGET)

    def _copy_if_missing(self, source: Path, destination: Path) -> None:
        if not source.exists():
            print(f"Modelo {source.name} não encontrado, pulando cópia.")
            return
        if destination.exists():
            print(f"Arquivo {destination.name} já existe. Mantendo configuração atual.")
            return
        shutil.copy2(source, destination)
        print(f"Arquivo {destination.name} criado a partir do modelo {source.name}.")

    def _venv_python(self) -> Path:
        if self.system.startswith("win"):
            return VENV_DIR / "Scripts" / "python.exe"
        return VENV_DIR / "bin" / "python"

    def _run_command(self, cmd: List[str]) -> None:
        print(f"Executando: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"Comando falhou com código {exc.returncode}: {' '.join(cmd)}")

    def _print_success_message(self) -> None:
        activate_cmd = (
            f"{VENV_DIR / 'Scripts' / 'activate.bat'}"
            if self.system.startswith("win")
            else f"source {VENV_DIR / 'bin' / 'activate'}"
        )
        python_executable = self._venv_python()
        guidance = [
            "Instalação concluída!",
            "Próximos passos:",
            f"1. Ative o ambiente virtual com: {activate_cmd}",
            f"2. Ajuste os arquivos {MONITOR_CONFIG_TARGET.name} e {API_CONFIG_TARGET.name} com suas credenciais.",
            f"3. Inicie a API proprietária com: {python_executable} api_server.py",
            f"4. Execute o painel web com: {python_executable} webapp.py",
            f"5. Opcionalmente, rode o monitor CLI com: {python_executable} main.py monitor",
        ]
        print("\n".join(guidance))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Instalador unificado para Windows e Linux do monitor de eCAC",
    )
    return parser.parse_args()


def main() -> None:
    parse_args()
    installer = Installer()
    installer.run()


if __name__ == "__main__":
    main()
