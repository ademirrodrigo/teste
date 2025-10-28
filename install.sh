#!/usr/bin/env bash
set -euo pipefail

# Script de instalação para ambientes Linux (Ubuntu/Debian).
# - Cria ambiente virtual
# - Instala dependências
# - Configura serviço systemd para o painel Streamlit

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="coletor-fiscal"
USER_SERVICE="$(whoami)"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

cat <<SERVICE | sudo tee /etc/systemd/system/${SERVICE_NAME}.service >/dev/null
[Unit]
Description=Coletor Fiscal v3.2 SaaS-Ready
After=network.target

[Service]
Type=simple
User=${USER_SERVICE}
WorkingDirectory=${APP_DIR}
Environment="PYTHONPATH=${APP_DIR}"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV_DIR}/bin/streamlit run ${APP_DIR}/web/app.py --server.port \${PORTA:-8501} --server.address 0.0.0.0
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

echo "Instalação concluída. O serviço ${SERVICE_NAME} está em execução."
