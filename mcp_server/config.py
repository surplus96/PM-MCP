import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "")
OBSIDIAN_VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH", "./obsidian_vault")

DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
RAW_PATH = os.path.join(DATA_ROOT, 'raw')
INTERIM_PATH = os.path.join(DATA_ROOT, 'interim')
PROCESSED_PATH = os.path.join(DATA_ROOT, 'processed')
CACHE_PATH = os.path.join(DATA_ROOT, 'cache')

# ---- Visualization presets & defaults ----
PRESENT_PRESET = os.getenv("PRESENT_PRESET", "modern").lower()

_PRESETS = {
    "modern": {
        "THEME_CHART_DAYS": 180,
        "PORTFOLIO_HISTORY_DAYS": 60,
        "YSCALE": "linear",
        "MA_WINDOWS": (20, 50),
        "COLORS": ["#2563eb", "#16a34a", "#f59e0b", "#ef4444", "#8b5cf6"],
        "NEWS_MAX": 7,
        "FILINGS_MAX": 7,
        "MPL_STYLE": "seaborn-v0_8",
    }
}
_p = _PRESETS.get(PRESENT_PRESET, _PRESETS["modern"])

PRESENT_THEME_CHART_DAYS = int(os.getenv("PRESENT_THEME_CHART_DAYS", str(_p["THEME_CHART_DAYS"])))
PRESENT_PORTFOLIO_HISTORY_DAYS = int(os.getenv("PRESENT_PORTFOLIO_HISTORY_DAYS", str(_p["PORTFOLIO_HISTORY_DAYS"])))
PRESENT_YSCALE = os.getenv("PRESENT_YSCALE", _p["YSCALE"])  # linear|log
PRESENT_MA_WINDOWS = tuple(
    int(x) for x in os.getenv("PRESENT_MA_WINDOWS", ",".join(map(str, _p["MA_WINDOWS"]))).split(',') if x.strip()
)
PRESENT_COLORS = [
    x.strip() for x in os.getenv("PRESENT_COLORS", ",".join(_p["COLORS"])) .split(',') if x.strip()
]
PRESENT_NEWS_MAX = int(os.getenv("PRESENT_NEWS_MAX", str(_p["NEWS_MAX"])))
PRESENT_FILINGS_MAX = int(os.getenv("PRESENT_FILINGS_MAX", str(_p["FILINGS_MAX"])))
PRESENT_MPL_STYLE = os.getenv("PRESENT_MPL_STYLE", _p["MPL_STYLE"])  # matplotlib style name

# Image output directory (writeable)
IMAGE_OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "/tmp/pm-mcp-images")
os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)

# ---- Scoring controls ----
SCORE_WEIGHTS = os.getenv("SCORE_WEIGHTS", "growth=0.25,profitability=0.25,valuation=0.25,quality=0.25")
SCORE_SECTOR_NEUTRAL = os.getenv("SCORE_SECTOR_NEUTRAL", "false").lower() in ("1","true","yes")
SECTOR_FACTOR_WEIGHTS = os.getenv("SECTOR_FACTOR_WEIGHTS")  # JSON 문자열(섹터별 팩터 가중)
EVENT_WEIGHTS_PATH = os.getenv("EVENT_WEIGHTS_PATH", os.path.join(os.path.dirname(__file__), "data", "event_weights.json"))

os.makedirs(RAW_PATH, exist_ok=True)
os.makedirs(INTERIM_PATH, exist_ok=True)
os.makedirs(PROCESSED_PATH, exist_ok=True)
os.makedirs(CACHE_PATH, exist_ok=True)
