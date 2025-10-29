#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="coletor-fiscal"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

sudo systemctl stop ${SERVICE_NAME} || true
sudo systemctl disable ${SERVICE_NAME} || true
sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service
sudo systemctl daemon-reload

read -rp "Deseja remover o ambiente virtual (.venv)? [s/N] " resposta
case "$resposta" in
  s|S|sim|SIM)
    rm -rf "$VENV_DIR"
    ;;
  *)
    echo "Ambiente virtual preservado."
    ;;
esac

echo "Remoção concluída."
