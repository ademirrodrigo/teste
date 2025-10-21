#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT=8000
RUN_SERVER=1
PYTHON_BIN=""

usage() {
    cat <<USAGE
Uso: ./02_linux_installer.sh [opções]

Opções:
  --host <ip>     Endereço que o servidor irá escutar (padrão: 0.0.0.0)
  --port <porta>  Porta do servidor (padrão: 8000)
  --skip-run      Instala dependências e sai sem iniciar o servidor
  -h, --help      Mostra esta ajuda
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --skip-run)
            RUN_SERVER=0
            shift 1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Opção desconhecida: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Python 3 não encontrado. Instale o Python 3.9 ou superior e tente novamente." >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    REPO_ROOT="$SCRIPT_DIR"
else
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
VENV_PATH="$REPO_ROOT/.venv"

if [[ ! -d "$VENV_PATH" ]]; then
    echo "[1/3] Criando ambiente virtual em $VENV_PATH"
    "$PYTHON_BIN" -m venv "$VENV_PATH"
else
    echo "Ambiente virtual já existe em $VENV_PATH"
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

echo "[2/3] Atualizando pip"
pip install --upgrade pip

echo "[3/3] Instalando dependências"
pip install -r "$REPO_ROOT/requirements.txt"

export PYTHONPATH="$REPO_ROOT"

echo "Banco de dados será criado automaticamente ao iniciar o servidor."

echo "Para personalizar a chave de segurança, defina a variável BPO_SECRET_KEY antes de iniciar."

if [[ "$RUN_SERVER" -eq 1 ]]; then
    echo "Iniciando servidor em http://$HOST:$PORT"
    exec uvicorn bpo_app.main:app --host "$HOST" --port "$PORT"
else
    echo "Instalação concluída. Para iniciar manualmente execute:"
    echo "  source $VENV_PATH/bin/activate"
    echo "  uvicorn bpo_app.main:app --host $HOST --port $PORT"
fi
