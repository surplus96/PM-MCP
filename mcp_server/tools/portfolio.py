from __future__ import annotations
from typing import List, Dict
import yfinance as yf
import pandas as pd


PHASES = ["적신호", "불안정", "유지", "상승"]


def evaluate_holdings(tickers: List[str]) -> List[Dict]:
    """간단 모멘텀 기준 페이즈 판정: 20일 수익률과 100일 대비 수준.
    (프로덕션에서는 리스크/변동성/이벤트 반영 확장)
    """
    results = []
    for t in tickers:
        hist = yf.download(t, period="6mo", interval="1d", progress=False, auto_adjust=True)
        if hist.empty or "Close" not in hist.columns:
            results.append({"ticker": t, "phase": "불안정", "note": "no data"})
            continue
        close_obj = hist["Close"]
        # yfinance가 다중 컬럼을 반환하는 경우 첫 컬럼 선택
        if isinstance(close_obj, pd.DataFrame):
            close_series = close_obj.iloc[:, 0]
        else:
            close_series = close_obj
        df = close_series.to_frame(name="Close").reset_index()
        df["ret20"] = df["Close"].pct_change(20)
        recent = df.iloc[-1]
        ret20 = float(recent.get("ret20", 0) or 0)
        if ret20 > 0.1:
            phase = "상승"
        elif ret20 > 0.02:
            phase = "유지"
        elif ret20 > -0.05:
            phase = "불안정"
        else:
            phase = "적신호"
        results.append({"ticker": t, "phase": phase, "ret20": round(ret20, 4)})
    return results
