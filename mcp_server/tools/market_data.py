from __future__ import annotations
import pandas as pd
import yfinance as yf
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
import os
from mcp_server.config import PROCESSED_PATH


def get_prices(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d") -> pd.DataFrame:
    start = start or (datetime.now().replace(year=datetime.now().year - 1).strftime('%Y-%m-%d'))
    end = end or datetime.now().strftime('%Y-%m-%d')
    data = yf.download(ticker, start=start, end=end, interval=interval, auto_adjust=True, progress=False)
    return data.reset_index()


def _safe_get(info: Dict[str, Any], key: str, default=None):
    try:
        v = info.get(key)
        if v is None:
            return default
        if isinstance(v, (int, float)):
                return float(v)
        return v
    except Exception:
        return default


def get_fundamentals_snapshot(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    info = {}
    try:
        info = tk.info if isinstance(getattr(tk, 'info', None), dict) else {}
    except Exception:
        info = {}

    fast = getattr(tk, 'fast_info', None)
    def _fast_get(name: str):
        try:
            return getattr(fast, name)
        except Exception:
            return None
    out = {
        "ticker": ticker,
        "market_cap": _fast_get('market_cap') if fast else None,
        "shares": _fast_get('shares') if fast else None,
        "currency": _fast_get('currency') if fast else None,
        "last_price": _fast_get('last_price') if fast else None,
        "sector": _safe_get(info, 'sector'),
        "industry": _safe_get(info, 'industry'),
        "pe": _safe_get(info, 'trailingPE'),
        "pb": _safe_get(info, 'priceToBook'),
        "eps": _safe_get(info, 'trailingEps'),
        "forwardEps": _safe_get(info, 'forwardEps'),
        "revenueGrowth": _safe_get(info, 'revenueGrowth'),
        "earningsQuarterlyGrowth": _safe_get(info, 'earningsQuarterlyGrowth'),
        "profitMargins": _safe_get(info, 'profitMargins'),
        "returnOnEquity": _safe_get(info, 'returnOnEquity'),
        "returnOnAssets": _safe_get(info, 'returnOnAssets'),
        "roic": _safe_get(info, 'returnOnCapitalEmployed'),
    }
    try:
        cf = getattr(tk, 'cashflow', None)
        if cf is not None and not cf.empty:
            for label in ("Free Cash Flow", "FreeCashFlow"):
                if label in cf.index:
                    fcf_series = cf.loc[label]
                    out["freeCashFlow"] = float(fcf_series.iloc[0]) if len(fcf_series) else None
                    break
    except Exception:
        pass
    return out


def get_momentum_metrics(ticker: str) -> dict:
    """안정적 모멘텀 계산: yfinance download 실패 시 Ticker().history로 폴백."""
    hist = None
    try:
        hist = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
    except Exception:
        hist = None
    if hist is None or hist.empty:
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="1y", interval="1d", auto_adjust=True)
        except Exception:
            hist = None
    if hist is None or hist.empty or "Close" not in hist.columns:
        return {"mom1": None, "mom3": None, "mom6": None, "mom12": None}
    close = hist["Close"].reset_index(drop=True)
    def ret(n):
        try:
            if len(close) < n:
                return None
            return float((close.iloc[-1] / close.iloc[-n]) - 1.0)
        except Exception:
            return None
    return {"mom1": ret(21), "mom3": ret(63), "mom6": ret(126), "mom12": ret(252)}


# -------- Token-saving helpers --------

def get_prices_paginated(ticker: str, start: Optional[str], end: Optional[str], interval: str = "1d", cursor: int = 0, page_size: int = 100) -> Tuple[list[dict], Optional[int]]:
    df = get_prices(ticker, start=start, end=end, interval=interval)
    records = df.to_dict(orient="records")
    slice_ = records[cursor: cursor + page_size]
    next_cursor = cursor + page_size if cursor + page_size < len(records) else None
    return slice_, next_cursor


def get_prices_summary(ticker: str, period: str = "1y", interval: str = "1d", agg: str = "W") -> dict:
    hist = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
    if hist.empty:
        return {"ticker": ticker, "count": 0}
    if agg:
        ohlc = hist.resample(agg).agg({"Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"})
    else:
        ohlc = hist
    desc = hist["Close"].describe().to_dict()
    return {"ticker": ticker, "count": int(len(hist)), "agg": agg, "ohlc_rows": int(len(ohlc)), "close_stats": {k: float(v) for k,v in desc.items()}}


def write_prices_csv(ticker: str, start: Optional[str], end: Optional[str], interval: str = "1d") -> str:
    df = get_prices(ticker, start=start, end=end, interval=interval)
    os.makedirs(PROCESSED_PATH, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    out_path = os.path.join(PROCESSED_PATH, f"prices_{ticker}_{date_str}.csv")
    df.to_csv(out_path, index=False)
    return out_path
