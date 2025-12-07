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
python - <<'PY'
from mcp_server.pipelines.theme_report import run_theme_report
p = run_theme_report("AI", ["AAPL","MSFT","NVDA"]) 
print(p)
PY
