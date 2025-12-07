#!/bin/zsh
set -euo pipefail
if [ -f .env ]; then
  set -a; source ./.env; set +a
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m mcp_server.mcp_app
