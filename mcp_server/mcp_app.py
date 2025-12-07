from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from typing import List, Dict, Optional
from datetime import datetime

from mcp_server.tools.market_data import get_prices
from mcp_server.tools.news_search import search_news
from mcp_server.tools.filings import fetch_recent_filings
from mcp_server.tools.analytics import rank_candidates, rank_tickers_with_fundamentals
from mcp_server.tools.portfolio import evaluate_holdings
from mcp_server.tools.reports import generate_report
from mcp_server.tools.obsidian import write_markdown
from mcp_server.pipelines.theme_report import run_theme_report
from mcp_server.pipelines.portfolio_report import run_portfolio_report
from mcp_server.tools.presenter import present_theme_overview, present_portfolio_overview
from mcp_server.tools.collect import compute_basic_metrics
from mcp_server.tools.parse import parse_holdings_text
import yfinance as yf
import pandas as pd

mcp = FastMCP(
    "PM-MCP",
    instructions=(
        "You are a portfolio manager sidekick. Use tools to fetch market data, news, SEC filings, rank candidates, "
        "evaluate holdings, generate reports, and write notes to the Obsidian vault."
    ),
    host="0.0.0.0",
    port=8010,
)


# Core tools
@mcp.tool()
async def market_get_prices(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d") -> List[Dict]:
    df = get_prices(ticker, start=start, end=end, interval=interval)
    return df.to_dict(orient="records")


@mcp.tool()
async def news_search(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    return search_news(queries, lookback_days=lookback_days, max_results=max_results)


@mcp.tool()
async def filings_fetch_recent(ticker: str, forms: Optional[List[str]] = None, limit: int = 10) -> List[Dict]:
    return fetch_recent_filings(ticker, forms=forms, limit=limit)


@mcp.tool()
async def analytics_rank(candidates: List[Dict], dip_weight: float = 0.12, use_dip_bonus: bool = True, auto_hydrate: bool = True) -> List[Dict]:
    # If factor fields are missing, hydrate via fundamentals-based ranking
    if auto_hydrate:
        needed = {"growth","profitability","valuation","quality"}
        needs_hydration = any(not (needed <= set(c.keys())) for c in candidates)
        if needs_hydration:
            tickers = [c.get("ticker") for c in candidates if c.get("ticker")]
            if tickers:
                return rank_tickers_with_fundamentals(tickers, dip_weight=dip_weight, use_dip_bonus=use_dip_bonus)
    return rank_candidates(candidates, dip_weight=dip_weight, use_dip_bonus=use_dip_bonus)


@mcp.tool()
async def portfolio_evaluate(holdings: List[str]) -> List[Dict]:
    return evaluate_holdings(holdings)


@mcp.tool()
async def portfolio_evaluate_detailed(holdings: List[str]) -> List[Dict]:
    """보유주 페이즈 + 기본 메트릭(모멘텀/변동성/낙폭/상관) 병합 결과."""
    base = evaluate_holdings(holdings)
    out: List[Dict] = []
    for e in base:
        t = e.get("ticker")
        metrics = compute_basic_metrics(t)
        merged = dict(metrics)
        merged.update({k: v for k, v in e.items() if k not in merged})
        out.append(merged)
    return out


def _latest_close(ticker: str) -> float | None:
    try:
        d = yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        if d.empty or "Close" not in d.columns:
            return None
        close_obj = d["Close"]
        if isinstance(close_obj, pd.DataFrame):
            close_series = close_obj.iloc[:, 0]
        else:
            close_series = close_obj
        return float(close_series.dropna().iloc[-1]) if not close_series.empty else None
    except Exception:
        return None


def _close_near_date(ticker: str, date_str: str) -> float | None:
    try:
        start = date_str
        d = yf.download(ticker, start=start, period="10d", interval="1d", progress=False, auto_adjust=True)
        if d.empty or "Close" not in d.columns:
            return None
        close_obj = d["Close"]
        if isinstance(close_obj, pd.DataFrame):
            s = close_obj.iloc[:, 0]
        else:
            s = close_obj
        s = s.dropna()
        return float(s.iloc[0]) if not s.empty else None
    except Exception:
        return None


@mcp.tool()
async def reports_generate(payload: Dict) -> str:
    return generate_report(payload)


@mcp.tool()
async def obsidian_write(note_path: str, front_matter: Optional[Dict] = None, body: str = "") -> str:
    return write_markdown(note_path, front_matter=front_matter, body=body)


# Natural language wrappers
@mcp.tool()
async def create_theme_report(theme: str, tickers_csv: str = "AAPL,MSFT,NVDA") -> str:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return run_theme_report(theme, tickers)


@mcp.tool()
async def create_portfolio_phase_report(tickers_csv: str) -> str:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return run_portfolio_report(tickers)


# Presenter (Claude-facing formatted output)
@mcp.tool()
async def present_theme(
    theme: str,
    tickers_csv: str = "AAPL,MSFT,NVDA",
    with_images: bool = False,
    chart_days: int = 90,
    yscale: str = "linear",
    ma_windows: Optional[List[int]] = None,
    colors: Optional[List[str]] = None,
) -> str:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return present_theme_overview(
        theme,
        tickers,
        with_images=with_images,
        chart_days=chart_days,
        yscale=yscale,
        ma_windows=tuple(ma_windows or (20, 50)),
        colors=colors,
    )


@mcp.tool()
async def present_portfolio(
    tickers_csv: str,
    with_images: bool = False,
    history_days: int = 30,
    yscale: str = "linear",
    ma_windows: Optional[List[int]] = None,
    colors: Optional[List[str]] = None,
) -> str:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return present_portfolio_overview(
        tickers,
        history_days=history_days,
        with_images=with_images,
        yscale=yscale,
        ma_windows=tuple(ma_windows or ()),
        colors=colors,
    )


@mcp.tool()
async def help_commands() -> str:
    return (
        "사용 예시(pm-mcp 네임스페이스):\n"
        "- 테마 추천: pm-mcp:propose_themes_tool(lookback_days=7, max_themes=5)\n"
        "- 테마 탐색: pm-mcp:explore_theme_tool(theme='AI')\n"
        "- 티커 제안: pm-mcp:propose_tickers_tool(theme='AI')\n"
        "- 정밀 분석 요약: pm-mcp:analyze_selection_tool(theme='AI', tickers=['AAPL','MSFT','NVDA'])\n"
        "- 간단 보유주 분석(자연어): pm-mcp:portfolio_analyze_nl_tool(holdings_text='AAPL@2024-10-01:185, LLY 2024-09-15 520, NVO')\n"
        "- 테마 리포트(이미지): pm-mcp:present_theme(theme='AI', tickers_csv='AAPL,MSFT,NVDA', with_images=True)\n"
        "- 포트폴리오 요약(이미지): pm-mcp:present_portfolio(tickers_csv='AAPL,MSFT,NVDA', with_images=True)\n"
        "(서버 선택 상태라면 접두사 'pm-mcp:' 생략 가능)\n"
    )


 

from mcp_server.tools.interaction import propose_themes, explore_theme, propose_tickers, analyze_selection

@mcp.tool()
async def propose_themes_tool(lookback_days: int = 7, max_themes: int = 5) -> List[str]:
    return propose_themes(lookback_days=lookback_days, max_themes=max_themes)


@mcp.tool()
async def explore_theme_tool(theme: str, lookback_days: int = 7) -> str:
    return explore_theme(theme, lookback_days=lookback_days)


@mcp.tool()
async def propose_tickers_tool(theme: str) -> List[str]:
    return propose_tickers(theme)


@mcp.tool()
async def analyze_selection_tool(theme: str, tickers: List[str]) -> str:
    return analyze_selection(theme, tickers)

from mcp_server.pipelines.dip_candidates import run_dip_candidates

@mcp.tool()
async def analyze_dip_candidates_tool(theme: str, tickers_csv: str | None = None, top_n: int = 5, drawdown_min: float = 0.2, ret10_min: float = 0.0, event_min: float = 0.5) -> Dict:
    tickers = [t.strip() for t in (tickers_csv.split(',') if tickers_csv else []) if t.strip()] or None
    return run_dip_candidates(theme, tickers=tickers, top_n=top_n, drawdown_min=drawdown_min, ret10_min=ret10_min, event_min=event_min, save=True)

@mcp.tool()
async def present_theme_save(theme: str, tickers_csv: str = "AAPL,MSFT,NVDA", with_images: bool = True) -> Dict:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    md = present_theme_overview(theme, tickers, with_images=with_images)
    date_str = datetime.now().strftime("%Y-%m-%d")
    note_path = write_markdown(f"Markets/{theme}/Overview {date_str}.md", front_matter={"type":"market","theme":theme,"date":date_str}, body=md)
    return {"note_path": note_path}


@mcp.tool()
async def present_portfolio_save(tickers_csv: str, with_images: bool = True) -> Dict:
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    from mcp_server.tools.presenter import present_portfolio_overview
    md = present_portfolio_overview(tickers, with_images=with_images)
    date_str = datetime.now().strftime("%Y-%m-%d")
    note_path = write_markdown(f"Portfolios/Overview {date_str}.md", front_matter={"type":"portfolio","date":date_str,"holdings":tickers}, body=md)
    return {"note_path": note_path}


@mcp.tool()
async def news_search_log_tool(queries: List[str], lookback_days: int = 7, max_results: int = 10, theme: str | None = None) -> Dict:
    res = search_news(queries, lookback_days=lookback_days, max_results=max_results)
    lines = ["# News Log", "", f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
    for blk in res:
        lines.append(f"## {blk.get('query')}")
        for h in blk.get('hits', []):
            title = h.get('title') or ''
            src = h.get('source') or ''
            url = h.get('url') or ''
            lines.append(f"- {title} ({src}) — {url}")
        lines.append("")
    body = "\n".join(lines)
    date_str = datetime.now().strftime("%Y-%m-%d")
    folder = f"Markets/{theme}/News Logs" if theme else "Markets/News Logs"
    note_path = write_markdown(f"{folder}/News {date_str}.md", front_matter={"type":"news","date":date_str,"theme":theme,"queries":queries}, body=body)
    return {"note_path": note_path}

@mcp.tool()
async def portfolio_analyze_nl_tool(holdings_text: str, save: bool = True) -> Dict:
    """자연어형 보유주 입력을 받아 컨디션/점수/손익을 요약하고(옵션) 리포트를 저장합니다.
    입력 예시: "AAPL@2024-10-01:185, LLY 2024-09-15 520, NVO"
    """
    parsed = parse_holdings_text(holdings_text)
    tickers = [p["ticker"] for p in parsed if p.get("ticker")]
    detailed = await portfolio_evaluate_detailed(tickers)
    ranked = rank_tickers_with_fundamentals(tickers, dip_weight=0.12, use_dip_bonus=True)
    rmap = {r["ticker"]: r for r in ranked}

    rows = []
    for p in parsed:
        t = p["ticker"]
        entry_date = p.get("entry_date")
        entry_price = p.get("entry_price")
        cur = _latest_close(t)
        ref = None
        if entry_date:
            ref = _close_near_date(t, entry_date)
        if entry_price is None:
            entry_price = ref
        pnl = None
        if entry_price and cur:
            pnl = (cur - float(entry_price)) / float(entry_price)
        base = rmap.get(t, {}).get("base_score")
        dip = rmap.get(t, {}).get("dip_bonus")
        total = rmap.get(t, {}).get("score")
        det = next((d for d in detailed if d.get("ticker") == t), {})
        rows.append({
            "ticker": t,
            "phase": det.get("phase"),
            "ret20": det.get("ret20"),
            "mom3": det.get("mom3"),
            "mom6": det.get("mom6"),
            "mom12": det.get("mom12"),
            "dd180": det.get("dd180"),
            "vol30": det.get("vol30"),
            "corr_spy": det.get("corr_spy"),
            "entry_date": entry_date,
            "entry_price": entry_price,
            "last": cur,
            "pnl": round(pnl, 4) if pnl is not None else None,
            "base_score": base,
            "dip_bonus": dip,
            "score": total,
        })

    def _fmt(x):
        if x is None:
            return ""
        if isinstance(x, float):
            return f"{x:.4f}"
        return str(x)

    headers = ["Ticker","Phase","ret20","mom3","mom6","mom12","dd180","vol30","corr_spy","EntryDate","EntryPrice","Last","PnL","Base","Dip","Score"]
    lines = ["## My Holdings Analysis","", "| " + " | ".join(headers) + " |", "|" + "|".join(["---"]*len(headers)) + "|"]
    for r in rows:
        line = "| " + " | ".join([
            _fmt(r.get("ticker")), _fmt(r.get("phase")), _fmt(r.get("ret20")),
            _fmt(r.get("mom3")), _fmt(r.get("mom6")), _fmt(r.get("mom12")),
            _fmt(r.get("dd180")), _fmt(r.get("vol30")), _fmt(r.get("corr_spy")),
            _fmt(r.get("entry_date")), _fmt(r.get("entry_price")), _fmt(r.get("last")), _fmt(r.get("pnl")),
            _fmt(r.get("base_score")), _fmt(r.get("dip_bonus")), _fmt(r.get("score")),
        ]) + " |"
        lines.append(line)
    md = "\n".join(lines)

    result: Dict = {"rows": rows}
    if save:
        date_str = datetime.now().strftime("%Y-%m-%d")
        note_path = write_markdown(
            f"Portfolios/Personal/Overview {date_str}.md",
            front_matter={"type": "portfolio", "date": date_str, "holdings_raw": holdings_text, "tickers": tickers},
            body=md,
        )
        result["note_path"] = note_path
    return result

# Token-saving market tools
@mcp.tool()
async def market_get_prices_paginated(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d", cursor: int = 0, page_size: int = 100) -> Dict:
    from mcp_server.tools.market_data import get_prices_paginated
    rows, next_cursor = get_prices_paginated(ticker, start, end, interval, cursor, page_size)
    return {"rows": rows, "next_cursor": next_cursor}


@mcp.tool()
async def market_get_prices_summary(ticker: str, period: str = "1y", interval: str = "1d", agg: str = "W") -> Dict:
    from mcp_server.tools.market_data import get_prices_summary
    return get_prices_summary(ticker, period=period, interval=interval, agg=agg)


@mcp.tool()
async def market_write_prices_csv(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d") -> Dict:
    from mcp_server.tools.market_data import write_prices_csv
    path = write_prices_csv(ticker, start=start, end=end, interval=interval)
    return {"csv_path": path}

if __name__ == "__main__":
    mcp.run(transport="stdio")
