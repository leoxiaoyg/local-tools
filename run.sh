#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# 默认直连 PyPI。需要代理时：export LT_PIP_PROXY=http://127.0.0.1:7897
if [[ -n "${LT_PIP_PROXY:-}" ]]; then
  export HTTP_PROXY="$LT_PIP_PROXY"
  export HTTPS_PROXY="$LT_PIP_PROXY"
fi
pip install -r requirements.txt -q
if [[ -n "${LT_PIP_PROXY:-}" ]]; then
  unset HTTP_PROXY HTTPS_PROXY
fi

port_in_use() {
  ss -tln 2>/dev/null | grep -q ":$1 " || \
  netstat -tln 2>/dev/null | grep -q ":$1 "
}

PORT=8000
if port_in_use "$PORT"; then
  echo "Port $PORT is already in use, trying 8080..."
  PORT=8080
  if port_in_use "$PORT"; then
    echo "Port 8080 is also in use, trying 8765..."
    PORT=8765
  fi
fi

echo
echo "Starting server at http://127.0.0.1:$PORT"
echo "Press Ctrl+C to stop."
echo
uvicorn app.main:app --reload --host 127.0.0.1 --port "$PORT"
