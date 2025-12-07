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
from mcp_server.pipelines.portfolio_report import run_portfolio_report
p = run_portfolio_report(["AAPL","MSFT","NVDA"]) 
print(p)
PY
