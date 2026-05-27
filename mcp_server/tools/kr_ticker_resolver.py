"""Korean company-name → 6-digit stock code resolver (FR-K01 확장).

Accepts inputs like ``"삼성전자"`` or ``"삼성"`` and returns the matching
KRX stock code (``"005930"``). Resolution strategy, in order:

    1. Cached ticker-name index (built once per process from pykrx).
    2. FinanceDataReader ``StockListing("KRX")`` if pykrx fails.
    3. Seed dict of the ~40 most-searched Korean names so simple demos
       work even with no network.

All callers should use :func:`resolve_korean_ticker` rather than reaching
into the pykrx module directly — it quietly returns the input unchanged
if the query is already a ticker (``"005930"``, ``"005930.KS"``, ``"AAPL"``),
so it's safe to wrap any upstream ticker parameter with it.
"""
from __future__ import annotations

import logging
import re
import threading
from functools import lru_cache
from typing import Optional

from mcp_server.tools.cache_manager import TTL, cache_manager

logger = logging.getLogger(__name__)


_KR_CHAR_RE = re.compile(r"[가-힣]")
_HAS_KR_CHAR = _KR_CHAR_RE.search


# Seed dictionary — hand-curated top names so the happy path works offline
# and tests don't depend on pykrx/KRX network. Extend as needed; canonical
# matches still come from the full pykrx-built index when available.
_SEED_NAME_TO_CODE: dict[str, str] = {
    "삼성전자": "005930",
    "sk하이닉스": "000660",
    "SK하이닉스": "000660",
    "LG에너지솔루션": "373220",
    "삼성바이오로직스": "207940",
    "현대차": "005380",
    "기아": "000270",
    "셀트리온": "068270",
    "네이버": "035420",
    "카카오": "035720",
    "포스코홀딩스": "005490",
    "LG화학": "051910",
    "삼성SDI": "006400",
    "에코프로비엠": "247540",
    "에코프로": "086520",
    "한화에어로스페이스": "012450",
    "한화오션": "042660",
    "HD현대중공업": "329180",
    "두산에너빌리티": "034020",
    "한국전력": "015760",
    "KB금융": "105560",
    "신한지주": "055550",
    "현대모비스": "012330",
    "한미반도체": "042700",
    "리노공업": "058470",
    "삼성물산": "028260",
    "LG전자": "066570",
    "삼성화재": "000810",
    "NAVER": "035420",
    "엔씨소프트": "036570",
    "크래프톤": "259960",
    "JYP": "035900",
    "하이브": "352820",
    "SM": "041510",
    "YG": "122870",
    "CJ": "001040",
    "LG": "003550",
    "SK": "034730",
    "두산": "000150",
    "한화": "000880",
    "현대글로비스": "086280",
    "대한항공": "003490",
    "KT": "030200",
    "포스코퓨처엠": "003670",
}


_index_lock = threading.Lock()
_index_built = False


def _build_index_from_pykrx() -> dict[str, str]:
    """One-shot build of ``name → code`` from pykrx.

    Uses a small threadpool because ``get_market_ticker_name`` is a single
    HTTP roundtrip per code. For ~2,600 KRX tickers this takes ~20–40s
    on a cold run and is cached for 24h afterwards.
    """
    try:
        from pykrx import stock
    except ImportError:
        logger.warning("pykrx not available — name resolution will rely on the seed dict.")
        return {}

    result: dict[str, str] = {}
    try:
        # The "K" parameter on recent pykrx means "KRX all-markets".
        codes: list[str] = []
        for market in ("KOSPI", "KOSDAQ"):
            try:
                codes.extend(stock.get_market_ticker_list(market=market))
            except Exception as e:  # noqa: BLE001
                logger.warning("pykrx ticker list for %s failed: %s", market, e)
        seen = set()
        for code in codes:
            if code in seen:
                continue
            seen.add(code)
            try:
                name = stock.get_market_ticker_name(code)
            except Exception:  # noqa: BLE001
                continue
            if name:
                result[name] = code
        logger.info("KR ticker-name index built: %d entries.", len(result))
    except Exception as e:  # noqa: BLE001
        logger.warning("KR ticker index build failed: %s", e)
    return result


def _build_index_from_fdr() -> dict[str, str]:
    """Fallback name→code index via FinanceDataReader.

    Cloud egress IPs (e.g. Hugging Face Spaces) are reliably blocked by
    the KRX endpoints PyKrx scrapes, so the primary path returns 0
    entries on that host. FDR hits a different upstream that those
    blocks miss, so it stands in as a self-healing alternative.
    """
    try:
        import FinanceDataReader as fdr
    except ImportError:
        logger.warning("FinanceDataReader not available — KR name resolution may be limited.")
        return {}
    try:
        df = fdr.StockListing("KRX")
    except Exception as e:  # noqa: BLE001
        logger.warning("FDR StockListing('KRX') failed: %s", e)
        return {}
    if df is None or df.empty:
        return {}
    code_col = next((c for c in ("Code", "Symbol") if c in df.columns), None)
    name_col = next((c for c in ("Name", "Korean", "한글명") if c in df.columns), None)
    if not code_col or not name_col:
        logger.warning("FDR listing missing expected columns; got %s", list(df.columns))
        return {}
    out: dict[str, str] = {}
    for code, name in zip(df[code_col].astype(str), df[name_col].astype(str)):
        code = code.strip().upper()
        name = name.strip()
        # KRX uses 6-char codes that are usually all-digit (regular common
        # stock) but can contain letters for special listings — REITs,
        # KONEX, ETN, A-prefixed stock-loan codes, etc. ``덕양에너젠`` for
        # example is ``0001A0``. Accept any 6-char alphanumeric.
        if name and len(code) == 6 and code.isalnum():
            out[name] = code
    logger.info("KR ticker-name index (FDR fallback) built: %d entries.", len(out))
    return out


def _get_cached_index() -> dict[str, str]:
    """Lazy-build the full pykrx index and cache in the shared cache_manager."""
    key = "kr_ticker_name_index_v1"
    cached = cache_manager.get(key)
    if isinstance(cached, dict) and cached:
        return cached
    # Single-builder guard so concurrent requests don't duplicate work.
    with _index_lock:
        cached = cache_manager.get(key)
        if isinstance(cached, dict) and cached:
            return cached
        idx = _build_index_from_pykrx()
        # PyKrx commonly returns empty on cloud-egress hosts (KRX bot
        # block); fall through to FDR before giving up so deployed
        # instances still resolve Korean company names.
        if not idx:
            idx = _build_index_from_fdr()
        # Merge seed → ensures well-known names always resolve even if
        # both upstreams returned empty.
        merged = {**_SEED_NAME_TO_CODE, **idx}
        cache_manager.set(key, merged, ttl=TTL.DAILY)
        return merged


def _looks_like_ticker(s: str) -> bool:
    """Return True for anything that is already a valid ticker surface."""
    t = s.strip().upper()
    if not t:
        return False
    if t.endswith(".KS") or t.endswith(".KQ"):
        return True
    if t.isdigit() and len(t) == 6:
        return True
    # Alphabetic US tickers (1–6 characters, optionally with dot like BRK.A)
    if re.fullmatch(r"[A-Z]{1,6}(\.[A-Z])?", t):
        return True
    return False


def _normalize_query(q: str) -> str:
    return re.sub(r"\s+", "", (q or "").strip())


@lru_cache(maxsize=512)
def _lookup_case_insensitive(index_items_tuple: tuple[tuple[str, str], ...], norm_query: str) -> Optional[str]:
    """Case-insensitive exact + startswith + substring matcher, cached."""
    if not norm_query:
        return None
    lower_q = norm_query.lower()
    # Exact (case-insensitive) match wins.
    for name, code in index_items_tuple:
        if name.lower() == lower_q:
            return code
    # Prefix match — "삼성" → "삼성전자".
    for name, code in index_items_tuple:
        if name.lower().startswith(lower_q):
            return code
    # Substring — final fallback so "퓨처엠" → "포스코퓨처엠".
    for name, code in index_items_tuple:
        if lower_q in name.lower():
            return code
    return None


def resolve_korean_ticker(query: str) -> str:
    """Return the 6-digit KRX code for a Korean name, or echo the input.

    Examples
    --------
    >>> resolve_korean_ticker("삼성전자")       # "005930"
    >>> resolve_korean_ticker("005930")         # "005930"  (passthrough)
    >>> resolve_korean_ticker("AAPL")           # "AAPL"    (passthrough)
    >>> resolve_korean_ticker("에코프로")       # "086520"  (seed hit)
    """
    if not query:
        return query
    raw = str(query).strip()
    if _looks_like_ticker(raw):
        return raw
    # If the query contains no Korean / Latin alphanumeric at all just
    # return as-is; upstream layers decide what to do.
    if not _HAS_KR_CHAR(raw) and not re.search(r"[A-Za-z]", raw):
        return raw

    norm = _normalize_query(raw)

    # 1) Seed first — fast and offline-friendly.
    seed_hit = _SEED_NAME_TO_CODE.get(norm) or _SEED_NAME_TO_CODE.get(norm.lower()) \
               or _SEED_NAME_TO_CODE.get(norm.upper())
    if seed_hit:
        return seed_hit

    # 2) Full pykrx index (lazy, cached 24h).
    try:
        index = _get_cached_index()
    except Exception:  # noqa: BLE001
        index = _SEED_NAME_TO_CODE
    if norm in index:
        return index[norm]
    # Partial / case-insensitive fallback.
    items = tuple(index.items())
    hit = _lookup_case_insensitive(items, norm)
    if hit:
        return hit
    return raw


def is_korean_name_query(query: str) -> bool:
    """True when the query contains Hangul — useful for detect_market branching."""
    return bool(query and _HAS_KR_CHAR(str(query)))


# ---------------------------------------------------------------------------
# Reverse lookup: 6-digit code → Korean company name
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _seed_code_to_name() -> dict[str, str]:
    """Invert ``_SEED_NAME_TO_CODE`` so a 6-digit code resolves to a name.

    When two seed entries map to the same code (e.g. "NAVER" and "네이버"
    both → 035420) the *last* one wins; we order the seed dict so the
    Korean name lands last → seed lookup returns Korean preferentially.
    """
    out: dict[str, str] = {}
    # Two-pass: English/Roman first, Korean second so Korean overwrites.
    roman = {n: c for n, c in _SEED_NAME_TO_CODE.items() if not _HAS_KR_CHAR(n)}
    korean = {n: c for n, c in _SEED_NAME_TO_CODE.items() if _HAS_KR_CHAR(n)}
    for name, code in roman.items():
        out[code] = name
    for name, code in korean.items():
        out[code] = name
    return out


def _strip_code(s: str) -> str:
    t = (s or "").strip().upper()
    if t.endswith(".KS") or t.endswith(".KQ"):
        t = t[:-3]
    return t


def code_to_name(code: str) -> Optional[str]:
    """Return the Korean company name for a 6-digit KRX code (or ``None``).

    Lookup order:
      1. Seed dict (offline, instant) — covers the most-asked-about names.
      2. Cached full pykrx index (lazy, 24 h cache shared with name → code).
      3. ``KoreanMarketAdapter.get_ticker_name`` as last resort.

    Returns ``None`` if the code is unknown or pykrx is unavailable. The
    caller is expected to fall back to whatever it had (e.g. show the raw
    code) rather than treating ``None`` as an error.
    """
    norm = _strip_code(code)
    if not (norm.isdigit() and len(norm) == 6):
        return None
    seed = _seed_code_to_name()
    if norm in seed:
        return seed[norm]
    # Full index reverse map (built lazily by ``_get_cached_index``).
    try:
        index = _get_cached_index()
        for name, c in index.items():
            if c == norm:
                return name
    except Exception:  # noqa: BLE001
        pass
    # Last-ditch: kr_market_data adapter wraps pykrx's ticker_name endpoint.
    try:
        from mcp_server.tools.kr_market_data import get_kr_adapter
        nm = get_kr_adapter().get_ticker_name(norm)
        if nm:
            return nm
    except Exception:  # noqa: BLE001
        pass
    return None


def label_kr_ticker(code: str) -> str:
    """Format a 6-digit code as ``"한글명 (코드)"`` when known, else ``"코드"``.

    Used by API responses and frontend formatters to give a single
    canonical label for KR tickers across every feature surface.
    """
    norm = _strip_code(code)
    name = code_to_name(norm)
    return f"{name} ({norm})" if name else norm
