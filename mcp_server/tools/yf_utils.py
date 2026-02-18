"""yfinance DataFrame column normalization utility.

yfinance >= 0.2.31 may return MultiIndex columns even for single tickers,
e.g. ("Close", "AAPL") instead of "Close".  This module provides a single
function that flattens columns so downstream code can always use df["Close"].
"""
from __future__ import annotations

import pandas as pd


def normalize_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance MultiIndex / comma-joined columns to simple names.

    Handles three cases:
    1. MultiIndex ("Close", "AAPL") -> "Close"
    2. Comma-joined "Close,AAPL"   -> "Close"
    3. Already flat "Close"        -> passthrough

    The function operates **in-place** on the column index and also returns
    the same DataFrame for convenience.
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        return df

    new_cols = []
    changed = False
    for col in df.columns:
        if isinstance(col, str) and "," in col:
            new_cols.append(col.split(",")[0].strip())
            changed = True
        else:
            new_cols.append(col)
    if changed:
        df.columns = new_cols

    return df
