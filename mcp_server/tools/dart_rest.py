"""DART OPEN API — direct REST client.

Replaces ``OpenDartReader.finstate_all()`` (which times out on the HF
Spaces cluster because its first call pulls a ~10 MB corp_code mapping
and fans out into multiple RPCs). This module hits a single endpoint
per ticker and reads the corp_code from a pre-baked JSON shipped with
the repo, so a cold call lands in ~1–3 s instead of ~30–60 s.

The output dict is intentionally shape-compatible with the older
``mcp_server.tools.dart.DartClient.get_financials`` so callers
(``financial_factors._dart_financials``) can swap the source without
re-wiring fields.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


DART_BASE_URL = "https://opendart.fss.or.kr/api"
CORP_CODES_PATH = Path(__file__).parent.parent / "data" / "dart_corp_codes.json"

# Korean account names DART uses on standard filings. Match is exact
# (modulo whitespace) — a substring match would let "기타수익" /
# "금융수익" / "보험료수익" shadow the real 매출액 row that arrives
# later in the response, and the first-wins picker would return the
# wrong number. Insurance/finance issuers do label their top line
# 영업수익 instead of 매출액, so both are accepted.
_REVENUE_KEYS = ("매출액", "영업수익", "매출")
_OPERATING_INCOME_KEYS = ("영업이익", "영업손익")
_NET_INCOME_KEYS = ("당기순이익", "당기순이익(손실)", "분기순이익")
_EQUITY_KEYS = ("자본총계",)
_ASSETS_KEYS = ("자산총계",)
_LIABILITIES_KEYS = ("부채총계",)


@lru_cache(maxsize=1)
def _load_corp_codes() -> dict[str, dict[str, str]]:
    """Load the pre-baked stock_code → {corp_code, name} mapping.

    ~3,900 listed KRX issuers, ~240 KB on disk. Loaded once per process
    and held in lru_cache so subsequent lookups are O(1) without disk IO.
    """
    if not CORP_CODES_PATH.exists():
        logger.warning("dart_corp_codes.json missing at %s", CORP_CODES_PATH)
        return {}
    try:
        with CORP_CODES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("DART corp_code mapping loaded: %d entries.", len(data))
        return data
    except Exception as e:  # noqa: BLE001
        logger.warning("Failed to load dart_corp_codes.json: %s", e)
        return {}


def _lookup_corp_code(stock_code: str) -> str | None:
    code = str(stock_code or "").strip().upper().replace(".KS", "").replace(".KQ", "")
    if not code:
        return None
    entry = _load_corp_codes().get(code)
    return entry.get("corp_code") if entry else None


def _pick(
    rows: list[dict],
    keys: tuple[str, ...],
    field: str,
    sj_filter: tuple[str, ...] | None = None,
    exact: bool = False,
) -> float | None:
    """First numeric value whose account_nm matches any keyword.

    ``sj_filter`` restricts the search to specific DART statement
    divisions (e.g. ``("IS","CIS")`` for income-statement items).
    Without it, IS / BS items collide with SCE / CIS duplicates and
    the first-match wins picks the wrong number — Samsung's "수익"
    in 기타수익/금융수익 used to shadow real 매출액, which is why an
    earlier version returned Operating_Margin ≈ 19.23 instead of 0.13.

    ``exact`` forces full string equality so a key like 매출액 doesn't
    swallow 매출액(전기) variants.
    """
    for r in rows:
        sj = r.get("sj_div", "")
        if sj_filter and sj not in sj_filter:
            continue
        nm = str(r.get("account_nm", "")).strip()
        if exact:
            matched = nm in keys
        else:
            matched = any(k in nm for k in keys)
        if not matched:
            continue
        raw = str(r.get(field, "")).replace(",", "").strip()
        if raw and raw not in ("-", "nan", ""):
            try:
                return float(raw)
            except ValueError:
                continue
    return None


def _safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None:
        return None
    try:
        if den == 0:
            return None
        return num / den
    except (TypeError, ZeroDivisionError):
        return None


def get_financials(
    stock_code: str,
    year: int | None = None,
    *,
    timeout: float = 8.0,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Return 8 standard ratios for a KRX issuer in a single REST call.

    Parameters
    ----------
    stock_code : 6-char KRX code (e.g. ``"005930"``).
    year : business year (default = last calendar year).
    timeout : per-call HTTP timeout in seconds (default 8 s — comfortable
              for the single fnlttSinglAcntAll round-trip).

    Returns
    -------
    dict with keys ``source``, ``year``, ``corp_code``, and zero or more
    of ``ROE``, ``ROA``, ``Operating_Margin``, ``Net_Margin``,
    ``Debt_to_Equity``, ``Debt_to_Asset``, ``Asset_Turnover``,
    ``Revenue_Growth``, ``EPS_Growth``. Missing fields → caller treats
    as NaN. Empty dict on hard failure (network / unknown ticker).
    """
    key = (api_key or os.getenv("DART_API_KEY", "")).strip()
    if not key:
        logger.debug("DART_API_KEY not set; skipping REST pull for %s.", stock_code)
        return {}

    corp_code = _lookup_corp_code(stock_code)
    if not corp_code:
        return {}

    use_year = int(year) if year else datetime.now().year - 1

    params = {
        "crtfc_key": key,
        "corp_code": corp_code,
        "bsns_year": str(use_year),
        "reprt_code": "11011",  # 사업보고서 (annual)
        "fs_div": "CFS",         # 연결재무제표 — falls back to OFS below if missing
    }

    try:
        r = requests.get(
            f"{DART_BASE_URL}/fnlttSinglAcntAll.json",
            params=params,
            timeout=timeout,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:  # noqa: BLE001
        logger.warning("DART REST call failed for %s (corp=%s): %s",
                       stock_code, corp_code, e)
        return {}

    status = str(data.get("status", "000"))
    rows = data.get("list") or []

    # If consolidated returns nothing, retry with separate financials —
    # smaller issuers often only file OFS.
    if status != "000" or not rows:
        try:
            params["fs_div"] = "OFS"
            r2 = requests.get(f"{DART_BASE_URL}/fnlttSinglAcntAll.json",
                              params=params, timeout=timeout)
            r2.raise_for_status()
            d2 = r2.json()
            if str(d2.get("status", "000")) == "000":
                rows = d2.get("list") or []
        except Exception:  # noqa: BLE001
            pass

    if not rows:
        return {"source": "dart_rest", "year": use_year, "corp_code": corp_code}

    # Income-statement items live in sj_div="IS" (or "CIS" for IFRS
    # comprehensive income variants). Balance-sheet items in "BS". The
    # statement-of-changes-in-equity (SCE) and cash-flow (CF) divisions
    # contain look-alike rows we must skip to avoid Samsung-style mis-picks.
    IS_DIV = ("IS", "CIS")
    BS_DIV = ("BS",)

    revenue = _pick(rows, _REVENUE_KEYS, "thstrm_amount", sj_filter=IS_DIV, exact=True)
    op_income = _pick(rows, _OPERATING_INCOME_KEYS, "thstrm_amount", sj_filter=IS_DIV, exact=True)
    net_income = _pick(rows, _NET_INCOME_KEYS, "thstrm_amount", sj_filter=IS_DIV, exact=True)
    equity = _pick(rows, _EQUITY_KEYS, "thstrm_amount", sj_filter=BS_DIV, exact=True)
    assets = _pick(rows, _ASSETS_KEYS, "thstrm_amount", sj_filter=BS_DIV, exact=True)
    liabilities = _pick(rows, _LIABILITIES_KEYS, "thstrm_amount", sj_filter=BS_DIV, exact=True)
    prev_revenue = _pick(rows, _REVENUE_KEYS, "frmtrm_amount", sj_filter=IS_DIV, exact=True)
    prev_net = _pick(rows, _NET_INCOME_KEYS, "frmtrm_amount", sj_filter=IS_DIV, exact=True)

    if liabilities is None and assets is not None and equity is not None:
        liabilities = assets - equity

    out: dict[str, Any] = {
        "source": "dart_rest",
        "year": use_year,
        "corp_code": corp_code,
    }
    if (roe := _safe_ratio(net_income, equity)) is not None:
        out["ROE"] = roe
    if (roa := _safe_ratio(net_income, assets)) is not None:
        out["ROA"] = roa
    if (op_margin := _safe_ratio(op_income, revenue)) is not None:
        out["Operating_Margin"] = op_margin
    if (net_margin := _safe_ratio(net_income, revenue)) is not None:
        out["Net_Margin"] = net_margin
    if (dte := _safe_ratio(liabilities, equity)) is not None:
        out["Debt_to_Equity"] = dte
    if (dta := _safe_ratio(liabilities, assets)) is not None:
        out["Debt_to_Asset"] = dta
    if (at := _safe_ratio(revenue, assets)) is not None:
        out["Asset_Turnover"] = at
    if revenue is not None and prev_revenue:
        out["Revenue_Growth"] = (revenue - prev_revenue) / prev_revenue
    if net_income is not None and prev_net:
        out["EPS_Growth"] = (net_income - prev_net) / prev_net

    return out
