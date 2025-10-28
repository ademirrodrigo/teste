#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="coletor-fiscal"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

cd "$APP_DIR"

git pull --ff-only

if [ -d "$VENV_DIR" ]; then
  source "$VENV_DIR/bin/activate"
  pip install -r requirements.txt
fi

sudo systemctl restart ${SERVICE_NAME}

echo "Atualização concluída. Serviço reiniciado."
