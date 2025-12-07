#!/bin/zsh
set -euo pipefail

# Load env if exists (robust)
if [ -f .env ]; then
  set -a
  source ./.env
  set +a
fi

# Create and activate venv
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m mcp_server.main
