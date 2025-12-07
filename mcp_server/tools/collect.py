from __future__ import annotations
from typing import Dict, Optional
from datetime import datetime, timedelta
import os
import json
import math

import pandas as pd
import yfinance as yf


CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, name)


def _pct(series: pd.Series, periods: int) -> Optional[float]:
    try:
        return float(series.pct_change(periods).iloc[-1])
    except Exception:
        return None


def _stdev(series: pd.Series, window: int) -> Optional[float]:
    try:
        return float(series.pct_change().rolling(window).std().iloc[-1])
    except Exception:
        return None


def _max_drawdown(series: pd.Series, lookback: int) -> Optional[float]:
    try:
        s = series.tail(lookback)
        roll_max = s.cummax()
        dd = (s - roll_max) / roll_max
        return float(dd.min())
    except Exception:
        return None


def _corr(a: pd.Series, b: pd.Series, window: int) -> Optional[float]:
    try:
        g = pd.concat([a.pct_change(), b.pct_change()], axis=1).dropna()
        if g.empty:
            return None
        return float(g.tail(window).corr().iloc[0, 1])
    except Exception:
        return None


def compute_basic_metrics(ticker: str, period: str = "2y", interval: str = "1d") -> Dict:
    """가격 기반 핵심 메트릭 산출: 모멘텀, 변동성, 최대낙폭, SPY 상관.
    결과는 data/cache/metrics_{TICKER}.json 에 캐시합니다.
    """
    cache_file = _cache_path(f"metrics_{ticker}.json")
    try:
        hist = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if hist.empty or "Close" not in hist.columns:
            raise RuntimeError("no price data")
        close_obj = hist["Close"]
        close = close_obj.iloc[:, 0] if isinstance(close_obj, pd.DataFrame) else close_obj
        close = close.dropna()

        # 모멘텀(일수 기준 대략치): 1M~12M
        mom1 = _pct(close, 21)
        mom3 = _pct(close, 63)
        mom6 = _pct(close, 126)
        mom12 = _pct(close, 252)
        ret20 = _pct(close, 20)

        # 변동성/최대낙폭/상관
        vol30 = _stdev(close, 30)
        vol60 = _stdev(close, 60)
        dd180 = _max_drawdown(close, 180)
        try:
            spy = yf.download("SPY", period=period, interval=interval, progress=False, auto_adjust=True)["Close"]
            spy = spy.iloc[:, 0] if isinstance(spy, pd.DataFrame) else spy
            corr_spy = _corr(close, spy, 90)
        except Exception:
            corr_spy = None

        data = {
            "ticker": ticker,
            "mom1": mom1, "mom3": mom3, "mom6": mom6, "mom12": mom12,
            "ret20": ret20,
            "vol30": vol30, "vol60": vol60,
            "dd180": dd180,
            "corr_spy": corr_spy,
            "asof": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return data
    except Exception:
        # 캐시가 있으면 반환
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"ticker": ticker}


def get_cached_metrics(ticker: str) -> Dict:
    cache_file = _cache_path(f"metrics_{ticker}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"ticker": ticker}
    return {"ticker": ticker}


