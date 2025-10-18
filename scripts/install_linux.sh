#!/usr/bin/env bash
set -euo pipefail

printf '\n==== Monitor eCAC :: Instalador Linux/VPS ===='\n

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [[ -z "$PYTHON_BIN" ]]; then
  cat <<'MSG'
[ERRO] Python 3 não localizado. Instale com:
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip
MSG
  exit 1
fi

echo "Usando Python: $(command -v "$PYTHON_BIN")"

set +e
"$PYTHON_BIN" install.py
EXIT_CODE=$?
set -e

if [[ $EXIT_CODE -ne 0 ]]; then
  echo "[ERRO] install.py retornou código $EXIT_CODE" >&2
  exit $EXIT_CODE
fi

echo "Instalação concluída. Revise as instruções acima para iniciar API, painel web e monitor CLI."
