#!/usr/bin/env sh
set -e

# Carrega variáveis do arquivo .env caso exista.
if [ -f "/app/.env" ]; then
  set -a
  . /app/.env
  set +a
fi

STREAMLIT_PORT="${PORTA:-8501}"
STREAMLIT_ADDR="${STREAMLIT_ADDRESS:-0.0.0.0}"

exec python -m streamlit run web/app.py --server.port "${STREAMLIT_PORT}" --server.address "${STREAMLIT_ADDR}"
