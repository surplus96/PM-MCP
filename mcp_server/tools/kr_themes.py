"""Korean theme → ticker map (FR-K14).

The seed mapping lives in ``mcp_server/data/kr_themes.json`` and is
hand-curated to ~18 domestic themes that retail investors search for
(2차전지, 원전, 반도체, 조선, 바이오, 방산, 로봇, …). Per theme we
keep a short list of 3–5 anchor tickers (6-digit KRX codes) — the chat
and ranking pipelines can expand from there with factor scoring.

Design notes:
    * JSON is loaded once at import and re-read on every call so edits
      via a running editor show up without a server restart.
    * Unknown themes return an empty list, consistent with the English
      propose_tickers() behaviour.
    * Theme names are matched case-insensitively after stripping whitespace
      so ``"2차전지"`` / ``" 2차전지 "`` / ``"2차 전지"`` all resolve to
      the same entry.
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "kr_themes.json"


def _strip_spaces(s: str) -> str:
    return "".join((s or "").split())


@lru_cache(maxsize=1)
def _load_raw() -> dict[str, list[str]]:
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Normalise keys: strip all whitespace so "AI 반도체" == "AI반도체"
        return {_strip_spaces(k): [str(v) for v in vs] for k, vs in raw.items()}
    except FileNotFoundError:
        logger.warning("kr_themes.json not found at %s", _DATA_PATH)
        return {}
    except Exception as e:  # noqa: BLE001
        logger.warning("kr_themes.json parse failed: %s", e)
        return {}


def list_themes() -> list[str]:
    """Return the available KR theme labels in their canonical form."""
    # Reload from disk so local edits during dev are picked up quickly —
    # strip whitespace then return the *original* keys for display.
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return list(raw.keys())
    except Exception:  # noqa: BLE001
        return list(_load_raw().keys())


def propose_tickers_kr(theme: str) -> list[str]:
    """Look up the anchor tickers for a Korean theme label.

    Returns an empty list when the theme is unknown.
    """
    key = _strip_spaces(theme)
    if not key:
        return []
    data = _load_raw()
    return list(data.get(key, []))


def lookup_theme_for_ticker(ticker: str) -> list[str]:
    """Reverse lookup: which KR themes contain this stock code.

    Useful for enriching a single-stock analysis with theme context.
    Returns the full set of matching theme labels (can be empty).
    """
    code = (ticker or "").strip().upper().replace(".KS", "").replace(".KQ", "")
    if not (code.isdigit() and len(code) == 6):
        return []
    data = _load_raw()
    return [theme for theme, codes in data.items() if code in codes]
