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
from mcp_server.tools.yf_utils import normalize_yf_columns

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
async def market_get_prices(ticker: str, start: Optional[str] = None, end: Optional[str] = None, interval: str = "1d", market: str = "US") -> List[Dict]:
    """가격 데이터 조회 (멀티 마켓 지원).

    Args:
        ticker: 종목 코드
        start: 시작일 (YYYY-MM-DD)
        end: 종료일 (YYYY-MM-DD)
        interval: 시간 간격 (1d, 1wk, 1mo 등)
        market: 시장 구분 ("US", "KR")

    Returns:
        가격 데이터 리스트

    Examples:
        - 미국 주식: market_get_prices("AAPL", market="US")
        - 한국 주식: market_get_prices("005930", market="KR") # 삼성전자
    """
    df = get_prices(ticker, start=start, end=end, interval=interval, market=market)
    return df.to_dict(orient="records")


@mcp.tool()
async def news_search(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    return search_news(queries, lookback_days=lookback_days, max_results=max_results)


@mcp.tool()
async def filings_fetch_recent(ticker: str, forms: Optional[List[str]] = None, limit: int = 10) -> List[Dict]:
    return fetch_recent_filings(ticker, forms=forms, limit=limit)


from mcp_server.tools.analytics import rank_tickers_with_fundamentals_async

@mcp.tool()
async def analytics_rank(candidates: List[Dict], dip_weight: float = 0.12, use_dip_bonus: bool = True, auto_hydrate: bool = True) -> List[Dict]:
    """후보 종목 랭킹 (비동기 병렬 처리)"""
    # If factor fields are missing, hydrate via fundamentals-based ranking
    if auto_hydrate:
        needed = {"growth","profitability","valuation","quality"}
        needs_hydration = any(not (needed <= set(c.keys())) for c in candidates)
        if needs_hydration:
            tickers = [c.get("ticker") for c in candidates if c.get("ticker")]
            if tickers:
                # 비동기 버전 사용으로 병렬 처리
                return await rank_tickers_with_fundamentals_async(tickers, dip_weight=dip_weight, use_dip_bonus=use_dip_bonus)
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
        d = normalize_yf_columns(
            yf.download(ticker, period="5d", interval="1d", progress=False, auto_adjust=True)
        )
        if d.empty or "Close" not in d.columns:
            return None
        close_series = d["Close"]
        return float(close_series.dropna().iloc[-1]) if not close_series.empty else None
    except Exception:
        return None


def _close_near_date(ticker: str, date_str: str) -> float | None:
    try:
        start = date_str
        d = normalize_yf_columns(
            yf.download(ticker, start=start, period="10d", interval="1d", progress=False, auto_adjust=True)
        )
        if d.empty or "Close" not in d.columns:
            return None
        s = d["Close"].dropna()
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


 

from mcp_server.tools.interaction import (
    propose_themes, explore_theme, propose_tickers, analyze_selection,
    propose_themes_async, explore_theme_async, analyze_selection_async
)

@mcp.tool()
async def propose_themes_tool(lookback_days: int = 7, max_themes: int = 5) -> List[str]:
    """투자 테마 추천 (비동기 병렬 처리)"""
    return await propose_themes_async(lookback_days=lookback_days, max_themes=max_themes)


@mcp.tool()
async def explore_theme_tool(theme: str, lookback_days: int = 7) -> str:
    """테마 상세 탐색 (비동기 버전)"""
    return await explore_theme_async(theme, lookback_days=lookback_days)


@mcp.tool()
async def propose_tickers_tool(theme: str) -> List[str]:
    return propose_tickers(theme)


@mcp.tool()
async def analyze_selection_tool(theme: str, tickers: List[str]) -> str:
    """선택 종목 분석 (비동기 병렬 처리)"""
    return await analyze_selection_async(theme, tickers)

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


# ===== 캐시 관리 도구 =====

@mcp.tool()
async def cache_stats() -> Dict:
    """캐시 통계 조회: 크기, 항목 수, 디렉토리 경로"""
    from mcp_server.tools.cache_manager import cache_manager
    return cache_manager.stats()


@mcp.tool()
async def cache_clear() -> Dict:
    """전체 캐시 삭제"""
    from mcp_server.tools.cache_manager import cache_manager
    count = cache_manager.clear()
    return {"cleared_items": count, "message": f"{count}개 캐시 항목이 삭제되었습니다."}


@mcp.tool()
async def cache_expire() -> Dict:
    """만료된 캐시 정리"""
    from mcp_server.tools.cache_manager import cache_manager
    count = cache_manager.expire()
    return {"expired_items": count, "message": f"{count}개 만료된 캐시가 정리되었습니다."}


# ===== 서킷 브레이커 관리 도구 =====

@mcp.tool()
async def circuit_status() -> Dict:
    """모든 서킷 브레이커 상태 조회"""
    from mcp_server.tools.resilience import get_all_circuit_status
    return get_all_circuit_status()


@mcp.tool()
async def circuit_reset(name: Optional[str] = None) -> Dict:
    """서킷 브레이커 리셋 (name 미지정 시 전체 리셋)"""
    from mcp_server.tools.resilience import CircuitBreaker, reset_all_circuits
    if name:
        cb = CircuitBreaker._instances.get(name)
        if cb:
            cb.reset()
            return {"reset": name, "message": f"서킷 '{name}'이 리셋되었습니다."}
        return {"error": f"서킷 '{name}'을 찾을 수 없습니다."}
    reset_all_circuits()
    return {"reset": "all", "message": "모든 서킷 브레이커가 리셋되었습니다."}


# ===== 스케줄러 관리 도구 =====

@mcp.tool()
async def scheduler_status() -> Dict:
    """스케줄러 상태 조회: 실행 중인 작업, 다음 실행 시간, 최근 이력"""
    from mcp_server.tools.scheduler import get_scheduler
    scheduler = get_scheduler()
    return scheduler.get_status()


@mcp.tool()
async def scheduler_start() -> Dict:
    """스케줄러 시작"""
    from mcp_server.tools.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.start()
    return {"status": "started", "message": "스케줄러가 시작되었습니다."}


@mcp.tool()
async def scheduler_stop() -> Dict:
    """스케줄러 중지"""
    from mcp_server.tools.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.stop()
    return {"status": "stopped", "message": "스케줄러가 중지되었습니다."}


@mcp.tool()
async def scheduler_run_job(job_id: str) -> Dict:
    """특정 작업 즉시 실행

    job_id 옵션:
    - market_refresh: 시장 데이터 갱신
    - news_scan: 뉴스 스캔
    - filings_check: SEC 공시 체크
    - weekly_report: 주간 리포트 생성
    - cache_cleanup: 캐시 정리
    - metrics_precompute: 메트릭 사전 계산
    """
    from mcp_server.tools.scheduler import get_scheduler
    scheduler = get_scheduler()
    return scheduler.run_job_now(job_id)


@mcp.tool()
async def scheduler_history(job_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """작업 실행 이력 조회"""
    from mcp_server.tools.scheduler import get_scheduler
    scheduler = get_scheduler()
    return scheduler.get_job_history(job_id, limit)


@mcp.tool()
async def watchlist_get() -> Dict:
    """현재 워치리스트 조회"""
    from mcp_server.config import WATCHLIST_PATH
    import json
    try:
        with open(WATCHLIST_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def watchlist_update(tickers: Optional[List[str]] = None, themes: Optional[List[str]] = None) -> Dict:
    """워치리스트 업데이트"""
    from mcp_server.config import WATCHLIST_PATH
    import json
    try:
        # 기존 데이터 로드
        try:
            with open(WATCHLIST_PATH, 'r') as f:
                data = json.load(f)
        except Exception:
            data = {"tickers": [], "themes": []}

        # 업데이트
        if tickers is not None:
            data["tickers"] = tickers
        if themes is not None:
            data["themes"] = themes
        data["updated"] = datetime.now().strftime("%Y-%m-%d")

        # 저장
        with open(WATCHLIST_PATH, 'w') as f:
            json.dump(data, f, indent=2)

        return {"status": "updated", "data": data}
    except Exception as e:
        return {"error": str(e)}


# ===== 고급 랭킹 도구 =====

@mcp.tool()
async def ranking_advanced(
    tickers_csv: str,
    use_sector_weights: bool = True,
    use_market_adjustment: bool = True,
    sector_neutral: bool = False,
    dip_weight: float = 0.12,
    use_dip_bonus: bool = True
) -> List[Dict]:
    """고급 랭킹: 섹터별 가중치 + 시장 상황 반영 + Z-score 정규화

    Features:
    - 6개 팩터: growth, profitability, valuation, quality, momentum, volatility
    - 섹터별 동적 가중치 (Technology vs Utilities 등 다른 기준)
    - 시장 상황(강세/약세/횡보) 반영 가중치 조정
    - Z-score 정규화 + 윈저화 (이상치 처리)

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        use_sector_weights: 섹터별 가중치 사용
        use_market_adjustment: 시장 상황 반영
        sector_neutral: 섹터 내 상대 비교 (True면 동일 섹터 내에서만 비교)
        dip_weight: 딥 보너스 가중치
        use_dip_bonus: 딥 보너스 사용 여부
    """
    from mcp_server.tools.ranking_engine import rank_advanced_async
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return await rank_advanced_async(
        tickers,
        use_sector_weights=use_sector_weights,
        use_market_adjustment=use_market_adjustment,
        sector_neutral=sector_neutral,
        dip_weight=dip_weight,
        use_dip_bonus=use_dip_bonus,
    )


@mcp.tool()
async def market_condition() -> Dict:
    """현재 시장 상황 감지: 강세(bull)/약세(bear)/횡보(neutral)"""
    from mcp_server.tools.ranking_engine import get_ranking_engine
    engine = get_ranking_engine()
    return engine.detect_market()


@mcp.tool()
async def sector_weights_info(sector: Optional[str] = None) -> Dict:
    """섹터별 가중치 정보 조회"""
    from mcp_server.tools.ranking_engine import SECTOR_WEIGHTS, DEFAULT_WEIGHTS
    if sector:
        weights = SECTOR_WEIGHTS.get(sector, DEFAULT_WEIGHTS)
        return {"sector": sector, "weights": weights}
    return {
        "sectors": list(SECTOR_WEIGHTS.keys()),
        "default_weights": DEFAULT_WEIGHTS,
        "sector_weights": SECTOR_WEIGHTS
    }


# ===== Alpha Vantage 기술적 지표 도구 =====

@mcp.tool()
async def technical_rsi(symbol: str, interval: str = "daily", time_period: int = 14) -> Dict:
    """RSI (Relative Strength Index) 조회

    Args:
        symbol: 종목 심볼
        interval: 'daily', 'weekly', 'monthly'
        time_period: RSI 기간 (기본 14)
    """
    from mcp_server.tools.alpha_vantage import get_rsi
    return get_rsi(symbol, interval=interval, time_period=time_period)


@mcp.tool()
async def technical_macd(
    symbol: str,
    interval: str = "daily",
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict:
    """MACD (Moving Average Convergence Divergence) 조회

    Args:
        symbol: 종목 심볼
        interval: 'daily', 'weekly', 'monthly'
        fast_period: 빠른 EMA 기간 (기본 12)
        slow_period: 느린 EMA 기간 (기본 26)
        signal_period: 시그널 EMA 기간 (기본 9)
    """
    from mcp_server.tools.alpha_vantage import get_macd
    return get_macd(symbol, interval=interval, fastperiod=fast_period,
                    slowperiod=slow_period, signalperiod=signal_period)


@mcp.tool()
async def technical_bbands(
    symbol: str,
    interval: str = "daily",
    time_period: int = 20,
    nbdevup: float = 2.0,
    nbdevdn: float = 2.0
) -> Dict:
    """Bollinger Bands 조회

    Args:
        symbol: 종목 심볼
        interval: 'daily', 'weekly', 'monthly'
        time_period: 기간 (기본 20)
        nbdevup: 상단 밴드 표준편차 배수
        nbdevdn: 하단 밴드 표준편차 배수
    """
    from mcp_server.tools.alpha_vantage import get_bbands
    return get_bbands(symbol, interval=interval, time_period=time_period,
                      nbdevup=nbdevup, nbdevdn=nbdevdn)


@mcp.tool()
async def technical_summary(symbol: str) -> Dict:
    """기술적 지표 종합 요약 (RSI + MACD + Bollinger Bands)

    신호 해석과 함께 종합 분석 제공
    """
    from mcp_server.tools.alpha_vantage import get_technical_summary
    return get_technical_summary(symbol)


@mcp.tool()
async def technical_sma(symbol: str, interval: str = "daily", time_period: int = 20) -> Dict:
    """SMA (Simple Moving Average) 조회"""
    from mcp_server.tools.alpha_vantage import get_sma
    return get_sma(symbol, interval=interval, time_period=time_period)


@mcp.tool()
async def technical_ema(symbol: str, interval: str = "daily", time_period: int = 20) -> Dict:
    """EMA (Exponential Moving Average) 조회"""
    from mcp_server.tools.alpha_vantage import get_ema
    return get_ema(symbol, interval=interval, time_period=time_period)


@mcp.tool()
async def technical_adx(symbol: str, interval: str = "daily", time_period: int = 14) -> Dict:
    """ADX (Average Directional Index) 조회 - 추세 강도 측정"""
    from mcp_server.tools.alpha_vantage import get_adx
    return get_adx(symbol, interval=interval, time_period=time_period)


# ===== Finnhub 데이터 도구 =====

@mcp.tool()
async def finnhub_news(
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict:
    """회사 관련 뉴스 조회 (감성 분석 포함)

    Args:
        symbol: 종목 심볼
        from_date: 시작일 (YYYY-MM-DD, 기본 7일 전)
        to_date: 종료일 (YYYY-MM-DD, 기본 오늘)
    """
    from mcp_server.tools.finnhub_api import get_company_news
    return get_company_news(symbol, from_date=from_date, to_date=to_date)


@mcp.tool()
async def finnhub_insider(symbol: str) -> Dict:
    """내부자 거래 내역 조회

    내부자 매수/매도 비율 기반 신호 제공
    """
    from mcp_server.tools.finnhub_api import get_insider_transactions
    return get_insider_transactions(symbol)


@mcp.tool()
async def finnhub_analyst(symbol: str) -> Dict:
    """애널리스트 추천 등급 조회

    컨센서스 (Strong Buy ~ Strong Sell) 및 트렌드 분석
    """
    from mcp_server.tools.finnhub_api import get_analyst_recommendations
    return get_analyst_recommendations(symbol)


@mcp.tool()
async def finnhub_earnings(
    symbol: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> Dict:
    """실적 발표 일정 조회

    Args:
        symbol: 종목 심볼 (없으면 전체 일정)
        from_date: 시작일
        to_date: 종료일 (기본 2주)
    """
    from mcp_server.tools.finnhub_api import get_earnings_calendar
    return get_earnings_calendar(symbol=symbol, from_date=from_date, to_date=to_date)


@mcp.tool()
async def finnhub_financials(symbol: str) -> Dict:
    """기본 재무 지표 조회

    - Valuation: P/E, P/B, P/S, EV/EBITDA
    - Profitability: ROE, ROA, Margins
    - Growth: Revenue/EPS Growth (3Y, 5Y)
    - Dividend: Yield, Payout Ratio
    """
    from mcp_server.tools.finnhub_api import get_basic_financials
    return get_basic_financials(symbol)


@mcp.tool()
async def finnhub_summary(symbol: str) -> Dict:
    """Finnhub 종합 요약 (뉴스+내부자+애널리스트+재무)

    종합 신호 (Bullish/Neutral/Bearish) 제공
    """
    from mcp_server.tools.finnhub_api import get_finnhub_summary
    return get_finnhub_summary(symbol)


# ===== 데이터 통합 도구 =====

@mcp.tool()
async def stock_comprehensive_analysis(symbol: str) -> Dict:
    """종목 종합 분석 (기술적+기본적+뉴스 감성 통합)

    멀티소스 데이터 통합:
    - Alpha Vantage: 기술적 지표 (RSI, MACD, BBands)
    - Finnhub: 재무, 애널리스트, 내부자
    - Yahoo Finance: 가격, 수익률, 변동성

    종합 신호 (Composite Signal) 제공
    """
    from mcp_server.tools.data_integrator import get_stock_analysis
    return get_stock_analysis(symbol)


@mcp.tool()
async def stock_compare(tickers_csv: str) -> Dict:
    """여러 종목 비교 분석

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록 (최대 5개 권장)

    Returns:
        종합 점수 기준 랭킹 및 비교 데이터
    """
    from mcp_server.tools.data_integrator import compare_stocks
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return compare_stocks(tickers[:5])  # 최대 5개


@mcp.tool()
async def stock_investment_signal(symbol: str) -> Dict:
    """투자 신호 요약 (의사결정 지원)

    Buy/Hold/Sell 신호와 근거, 리스크 요소 제공
    """
    from mcp_server.tools.data_integrator import get_investment_signal
    return get_investment_signal(symbol)


# ===== 뉴스 감성 분석 도구 =====

@mcp.tool()
async def news_sentiment_analyze(
    tickers_csv: str,
    lookback_days: int = 7,
    use_llm: bool = False
) -> Dict:
    """종목별 뉴스 감성 분석

    키워드 기반 + 옵션으로 LLM 분석 지원

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        lookback_days: 뉴스 검색 기간 (일)
        use_llm: LLM 기반 고급 분석 사용 (Perplexity API 필요)

    Returns:
        - overall: bullish/bearish/neutral 감성
        - score: -1.0 ~ 1.0 점수
        - sentiment_distribution: 감성 분포
        - timeline: 날짜별 뉴스 타임라인
        - investment_signal: 투자 신호 해석
    """
    from mcp_server.tools.news_sentiment import analyze_ticker_news
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]

    if len(tickers) == 1:
        return analyze_ticker_news(tickers[0], lookback_days=lookback_days, use_llm=use_llm)

    # 여러 종목인 경우
    results = {}
    for ticker in tickers[:5]:  # 최대 5개
        results[ticker] = analyze_ticker_news(ticker, lookback_days=lookback_days, use_llm=use_llm)
    return results


@mcp.tool()
async def news_sentiment_compare(
    tickers_csv: str,
    lookback_days: int = 7
) -> Dict:
    """여러 종목 뉴스 감성 비교

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        lookback_days: 뉴스 검색 기간

    Returns:
        - tickers: 종목별 감성 점수 및 랭킹
        - most_positive: 가장 긍정적인 종목
        - most_negative: 가장 부정적인 종목
    """
    from mcp_server.tools.news_sentiment import compare_tickers_sentiment
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    return compare_tickers_sentiment(tickers[:10], lookback_days=lookback_days)


@mcp.tool()
async def news_sentiment_text(text: str) -> Dict:
    """텍스트 감성 분석 (단일 텍스트)

    뉴스 헤드라인이나 기사 본문의 감성 분석

    Args:
        text: 분석할 텍스트

    Returns:
        - sentiment: positive/negative/neutral
        - score: 감성 점수
        - impact: 영향도
        - matched_keywords: 매칭된 키워드
    """
    from mcp_server.tools.news_sentiment import get_analyzer
    analyzer = get_analyzer()
    sentiment = analyzer.analyze_text(text)
    impact = analyzer.analyze_impact(text)
    return {
        **sentiment,
        "impact": impact["impact"],
        "impact_score": impact["score"],
        "impact_factors": impact["factors"]
    }


@mcp.tool()
async def news_deduplicate(news_json: str) -> Dict:
    """뉴스 중복 제거 및 클러스터링

    Args:
        news_json: 뉴스 리스트 JSON 문자열
                   예: '[{"title": "...", "snippet": "..."}]'

    Returns:
        - unique_count: 중복 제거 후 뉴스 수
        - clusters: 주제별 클러스터
        - items: 중복 제거된 뉴스 리스트
    """
    from mcp_server.tools.news_sentiment import get_deduplicator, NewsDeduplicator
    import json

    try:
        news_items = json.loads(news_json)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON format"}

    deduplicator = get_deduplicator()
    unique = deduplicator.deduplicate(news_items)
    clusters = deduplicator.cluster_by_topic(unique)

    return {
        "original_count": len(news_items),
        "unique_count": len(unique),
        "removed": len(news_items) - len(unique),
        "clusters": {k: len(v) for k, v in clusters.items()},
        "items": unique
    }


@mcp.tool()
async def news_timeline(
    ticker: str,
    lookback_days: int = 14
) -> Dict:
    """종목 뉴스 타임라인 생성

    날짜별로 정리된 뉴스 흐름과 감성 변화 추적

    Args:
        ticker: 종목 심볼
        lookback_days: 검색 기간 (일)

    Returns:
        - timeline: 날짜별 뉴스 목록
        - sentiment_trend: 날짜별 감성 점수 추이
    """
    from mcp_server.tools.news_sentiment import analyze_ticker_news

    result = analyze_ticker_news(ticker, lookback_days=lookback_days, use_llm=False)
    timeline = result.get("timeline", [])

    # 감성 추이 계산
    sentiment_trend = []
    for day in timeline:
        date = day.get("date", "unknown")
        items = day.get("items", [])
        if items:
            avg_score = sum(i.get("sentiment_score", 0) for i in items) / len(items)
            sentiment_trend.append({
                "date": date,
                "score": round(avg_score, 3),
                "count": len(items)
            })

    return {
        "ticker": ticker.upper(),
        "period_days": lookback_days,
        "timeline": timeline,
        "sentiment_trend": sentiment_trend,
        "overall": result.get("overall", "neutral"),
        "investment_signal": result.get("investment_signal", "")
    }


@mcp.tool()
async def news_impact_keywords() -> Dict:
    """뉴스 영향도 평가에 사용되는 키워드 목록 조회

    어떤 키워드가 고/중/저 영향도로 분류되는지 확인
    """
    from mcp_server.tools.news_sentiment import IMPACT_KEYWORDS, SENTIMENT_KEYWORDS

    return {
        "impact_keywords": {
            level: {
                "keywords": data["keywords"],
                "weight": data["weight"]
            }
            for level, data in IMPACT_KEYWORDS.items()
        },
        "sentiment_keywords": {
            category: {
                "sample_keywords": data["keywords"][:5],
                "total_count": len(data["keywords"]),
                "score": data["score"]
            }
            for category, data in SENTIMENT_KEYWORDS.items()
        }
    }


# ===== 포트폴리오 관리 도구 =====

@mcp.tool()
async def portfolio_pnl(holdings_text: str, cash: float = 0) -> Dict:
    """포트폴리오 손익 추적

    Args:
        holdings_text: 보유 종목 텍스트
                      형식: "TICKER:SHARES@ENTRY_PRICE, ..."
                      예: "AAPL:10@150, MSFT:5@400, GOOGL:3@140"
        cash: 현금 보유액

    Returns:
        - 종목별 손익 (금액, 퍼센트)
        - 총 포트폴리오 가치
        - 승률 (이익 종목 비율)
        - 최고/최저 성과 종목
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, get_portfolio_summary
    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다. 형식: TICKER:SHARES@PRICE"}
    return get_portfolio_summary(holdings, cash)


@mcp.tool()
async def portfolio_rebalance(
    holdings_text: str,
    target_weights_text: str,
    cash: float = 0,
    threshold: float = 5.0
) -> Dict:
    """포트폴리오 리밸런싱 체크

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES@PRICE, ...)
        target_weights_text: 목표 비중 (TICKER:WEIGHT%, ...)
                            예: "AAPL:30, MSFT:25, GOOGL:25, CASH:20"
        cash: 현금 보유액
        threshold: 리밸런싱 임계값 (%, 기본 5%)

    Returns:
        - 리밸런싱 필요 여부
        - 종목별 편차 및 조정 필요 수량
        - 총 편차
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, check_rebalancing, Holding

    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}

    # 목표 비중 파싱
    try:
        weights = {}
        for part in target_weights_text.replace(" ", "").split(","):
            if ":" in part:
                ticker, weight = part.split(":", 1)
                weights[ticker.upper()] = float(weight) / 100
    except Exception:
        return {"error": "목표 비중을 파싱할 수 없습니다. 형식: TICKER:WEIGHT%"}

    # 목표 비중 설정
    for h in holdings:
        if h.ticker in weights:
            h.target_weight = weights[h.ticker]

    return check_rebalancing(holdings, cash, threshold / 100)


@mcp.tool()
async def portfolio_dividends(holdings_text: str, days_ahead: int = 90) -> Dict:
    """포트폴리오 배당 캘린더

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES, ...)
        days_ahead: 향후 조회 기간 (일)

    Returns:
        - 예정된 배당락일
        - 예상 배당금
        - 연간 총 배당 수입
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, get_dividend_calendar
    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}
    return get_dividend_calendar(holdings, days_ahead)


@mcp.tool()
async def portfolio_alerts(holdings_text: str, targets_text: Optional[str] = None) -> Dict:
    """포트폴리오 가격 알림 체크

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES@ENTRY, ...)
        targets_text: 목표가/손절가 설정 (TICKER:TARGET:STOP, ...)
                     예: "AAPL:200:140, MSFT:450:350"

    Returns:
        - 목표가 도달 알림
        - 손절가 도달 알림
        - 목표/손절 근접 경고
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, check_price_alerts

    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}

    # 목표가/손절가 파싱
    if targets_text:
        try:
            for part in targets_text.replace(" ", "").split(","):
                if ":" in part:
                    parts = part.split(":")
                    ticker = parts[0].upper()
                    for h in holdings:
                        if h.ticker == ticker:
                            if len(parts) > 1 and parts[1]:
                                h.target_price = float(parts[1])
                            if len(parts) > 2 and parts[2]:
                                h.stop_loss = float(parts[2])
        except Exception:
            pass

    return check_price_alerts(holdings)


@mcp.tool()
async def portfolio_correlation(tickers_csv: str, period: str = "1y") -> Dict:
    """포트폴리오 상관관계 분석

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        period: 분석 기간 (1y, 6mo, 3mo 등)

    Returns:
        - 상관관계 매트릭스
        - 종목 쌍별 상관관계
        - 다각화 점수 (낮은 상관관계 = 높은 점수)
        - 다각화 등급
    """
    from mcp_server.tools.portfolio_manager import analyze_correlation
    tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]
    if len(tickers) < 2:
        return {"error": "최소 2개 종목이 필요합니다."}
    return analyze_correlation(tickers, period)


@mcp.tool()
async def portfolio_sectors(holdings_text: str) -> Dict:
    """포트폴리오 섹터 익스포저 분석

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES, ...)

    Returns:
        - 섹터별 비중
        - 집중도 지수 (HHI)
        - 집중도 경고
        - 분산 추천
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, analyze_sector_exposure
    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}
    return analyze_sector_exposure(holdings)


@mcp.tool()
async def portfolio_comprehensive(holdings_text: str, cash: float = 0) -> Dict:
    """포트폴리오 종합 분석

    손익, 리밸런싱, 배당, 알림, 상관관계, 섹터 분석 통합

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES@ENTRY, ...)
        cash: 현금 보유액

    Returns:
        - 건강도 점수 및 등급
        - 손익 요약
        - 리밸런싱 필요 여부
        - 배당 정보
        - 가격 알림
        - 상관관계 분석
        - 섹터 분석
    """
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, analyze_portfolio_comprehensive
    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}
    return analyze_portfolio_comprehensive(holdings, cash)


@mcp.tool()
async def portfolio_save(
    name: str,
    holdings_text: str,
    cash: float = 0
) -> Dict:
    """포트폴리오 저장

    Args:
        name: 포트폴리오 이름
        holdings_text: 보유 종목 (TICKER:SHARES@ENTRY, ...)
        cash: 현금 보유액

    Returns:
        저장된 파일 경로
    """
    from mcp_server.tools.portfolio_manager import (
        create_holdings_from_text, save_portfolio, Portfolio
    )

    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}

    portfolio = Portfolio(name=name, holdings=holdings, cash=cash)
    filepath = save_portfolio(portfolio, name)

    return {
        "saved": True,
        "name": name,
        "filepath": filepath,
        "holdings_count": len(holdings),
        "cash": cash
    }


@mcp.tool()
async def portfolio_load(name: str) -> Dict:
    """저장된 포트폴리오 로드

    Args:
        name: 포트폴리오 이름

    Returns:
        포트폴리오 정보
    """
    from mcp_server.tools.portfolio_manager import load_portfolio

    portfolio = load_portfolio(name)
    if not portfolio:
        return {"error": f"포트폴리오 '{name}'을 찾을 수 없습니다."}

    return {
        "name": portfolio.name,
        "holdings": [h.to_dict() for h in portfolio.holdings],
        "cash": portfolio.cash,
        "created_at": portfolio.created_at,
        "updated_at": portfolio.updated_at
    }


@mcp.tool()
async def portfolio_list() -> Dict:
    """저장된 포트폴리오 목록 조회"""
    from mcp_server.tools.portfolio_manager import list_portfolios

    portfolios = list_portfolios()
    return {
        "portfolios": portfolios,
        "count": len(portfolios)
    }


# ===== 시각화 도구 =====

@mcp.tool()
async def chart_candlestick(
    ticker: str,
    period: str = "6mo",
    show_volume: bool = True,
    ma_periods: Optional[str] = "20,50",
    save_as: Optional[str] = None
) -> Dict:
    """캔들스틱 차트 생성

    Args:
        ticker: 종목 심볼
        period: 기간 (1mo, 3mo, 6mo, 1y, 2y)
        show_volume: 거래량 표시
        ma_periods: 이동평균선 기간 (쉼표 구분, 예: "20,50,200")
        save_as: 저장 파일명 (없으면 저장 안함)

    Returns:
        - chart_html: HTML 차트 코드
        - saved_path: 저장된 파일 경로 (저장한 경우)
    """
    from mcp_server.tools.visualizer import create_candlestick_chart, save_chart, chart_to_html

    ma_list = [int(x.strip()) for x in ma_periods.split(",")] if ma_periods else None
    fig = create_candlestick_chart(ticker, period, show_volume, ma_list)

    result = {"ticker": ticker, "period": period}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_technical(
    ticker: str,
    period: str = "6mo",
    indicators: str = "rsi,macd",
    save_as: Optional[str] = None
) -> Dict:
    """기술적 지표 차트 생성

    Args:
        ticker: 종목 심볼
        period: 기간
        indicators: 지표 (쉼표 구분: rsi, macd, bbands, volume)
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
    """
    from mcp_server.tools.visualizer import create_technical_chart, save_chart, chart_to_html

    ind_list = [x.strip() for x in indicators.split(",")]
    fig = create_technical_chart(ticker, period, ind_list)

    result = {"ticker": ticker, "period": period, "indicators": ind_list}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_comparison(
    tickers_csv: str,
    period: str = "1y",
    normalize: bool = True,
    save_as: Optional[str] = None
) -> Dict:
    """종목 비교 차트 생성

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        period: 기간
        normalize: 100 기준 정규화 (시작점 = 100)
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
    """
    from mcp_server.tools.visualizer import create_comparison_chart, save_chart, chart_to_html

    tickers = [t.strip() for t in tickers_csv.split(",")]
    fig = create_comparison_chart(tickers, period, normalize)

    result = {"tickers": tickers, "period": period, "normalized": normalize}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_relative_strength(
    ticker: str,
    benchmark: str = "SPY",
    period: str = "1y",
    save_as: Optional[str] = None
) -> Dict:
    """상대강도 차트 생성 (vs 벤치마크)

    Args:
        ticker: 종목 심볼
        benchmark: 벤치마크 심볼 (기본 SPY)
        period: 기간
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
    """
    from mcp_server.tools.visualizer import create_relative_strength_chart, save_chart, chart_to_html

    fig = create_relative_strength_chart(ticker, benchmark, period)

    result = {"ticker": ticker, "benchmark": benchmark, "period": period}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_returns_distribution(
    ticker: str,
    period: str = "1y",
    save_as: Optional[str] = None
) -> Dict:
    """수익률 분포 히스토그램

    Args:
        ticker: 종목 심볼
        period: 기간
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
        - statistics: 평균, 표준편차, 왜도, 첨도, VaR
    """
    from mcp_server.tools.visualizer import create_returns_distribution, save_chart, chart_to_html, _get_ohlcv
    import numpy as np

    fig = create_returns_distribution(ticker, period)

    # 통계 계산
    df = _get_ohlcv(ticker, period)
    stats = {}
    if not df.empty:
        returns = df["Close"].pct_change().dropna() * 100
        stats = {
            "mean": round(float(returns.mean()), 3),
            "std": round(float(returns.std()), 3),
            "skewness": round(float(returns.skew()), 3),
            "kurtosis": round(float(returns.kurtosis()), 3),
            "var_5pct": round(float(returns.quantile(0.05)), 3),
            "max_daily_gain": round(float(returns.max()), 3),
            "max_daily_loss": round(float(returns.min()), 3)
        }

    result = {"ticker": ticker, "period": period, "statistics": stats}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_portfolio_allocation(
    holdings_text: str,
    save_as: Optional[str] = None
) -> Dict:
    """포트폴리오 비중 파이 차트

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES@PRICE 또는 TICKER:VALUE)
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
    """
    from mcp_server.tools.visualizer import create_portfolio_pie_chart, save_chart, chart_to_html
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, _get_current_price

    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}

    # 현재 가치 계산
    values = {}
    for h in holdings:
        price = _get_current_price(h.ticker)
        if price:
            values[h.ticker] = h.shares * price

    fig = create_portfolio_pie_chart(values)

    result = {"holdings_count": len(values), "total_value": sum(values.values())}

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_correlation_heatmap(
    tickers_csv: str,
    period: str = "1y",
    save_as: Optional[str] = None
) -> Dict:
    """상관관계 히트맵

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        period: 기간
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
        - correlation_matrix: 상관관계 매트릭스
    """
    from mcp_server.tools.visualizer import create_correlation_heatmap, save_chart, chart_to_html
    from mcp_server.tools.portfolio_manager import analyze_correlation

    tickers = [t.strip() for t in tickers_csv.split(",")]
    corr_result = analyze_correlation(tickers, period)

    if "error" in corr_result:
        return corr_result

    fig = create_correlation_heatmap(corr_result["correlation_matrix"])

    result = {
        "tickers": tickers,
        "period": period,
        "diversification_score": corr_result.get("diversification_score"),
        "average_correlation": corr_result.get("average_correlation")
    }

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_sector_allocation(
    holdings_text: str,
    save_as: Optional[str] = None
) -> Dict:
    """섹터별 비중 막대 차트

    Args:
        holdings_text: 보유 종목 (TICKER:SHARES, ...)
        save_as: 저장 파일명

    Returns:
        - chart_html: HTML 차트 코드
        - sectors: 섹터별 비중 데이터
    """
    from mcp_server.tools.visualizer import create_sector_bar_chart, save_chart, chart_to_html
    from mcp_server.tools.portfolio_manager import create_holdings_from_text, analyze_sector_exposure

    holdings = create_holdings_from_text(holdings_text)
    if not holdings:
        return {"error": "보유 종목을 파싱할 수 없습니다."}

    sector_result = analyze_sector_exposure(holdings)
    if "error" in sector_result:
        return sector_result

    fig = create_sector_bar_chart(sector_result["sectors"])

    result = {
        "sector_count": sector_result["sector_count"],
        "concentration_level": sector_result["concentration_level"],
        "sectors": sector_result["sectors"]
    }

    if save_as:
        path = save_chart(fig, save_as, format="html")
        result["saved_path"] = path

    result["chart_html"] = chart_to_html(fig)
    return result


@mcp.tool()
async def chart_stock_dashboard(
    ticker: str,
    period: str = "6mo",
    save_as: Optional[str] = None
) -> Dict:
    """종목 종합 대시보드 (4개 차트)

    캔들스틱, 기술적 지표, 수익률 분포, 상대강도 차트 통합

    Args:
        ticker: 종목 심볼
        period: 기간
        save_as: 저장 파일명 prefix

    Returns:
        - charts: 각 차트 HTML
        - saved_paths: 저장된 파일 경로들
    """
    from mcp_server.tools.visualizer import create_stock_dashboard, save_chart, chart_to_html

    dashboard = create_stock_dashboard(ticker, period)

    result = {
        "ticker": ticker,
        "period": period,
        "charts": {}
    }

    saved_paths = {}
    for name, fig in dashboard.items():
        result["charts"][name] = chart_to_html(fig)
        if save_as:
            path = save_chart(fig, f"{save_as}_{name}", format="html")
            saved_paths[name] = path

    if save_as:
        result["saved_paths"] = saved_paths

    return result


# ===== 데이터 품질 검증 도구 =====

@mcp.tool()
async def data_validate(ticker: str, period: str = "1y") -> Dict:
    """데이터 품질 검증

    가격 데이터의 품질을 검사하고 품질 점수 및 등급 제공

    검사 항목:
    - 필수 컬럼 존재 여부
    - 데이터 타입 검사
    - 누락 데이터 (NaN)
    - 0값 검사
    - 이상치 탐지 (3σ 기준)
    - 가격 정합성 (High >= Low 등)
    - 거래량 검사
    - 날짜 갭 검사
    - 극단적 가격 변동 검사

    Args:
        ticker: 종목 심볼
        period: 검증 기간 (1mo, 3mo, 6mo, 1y, 2y)

    Returns:
        - quality_score: 품질 점수 (0-100)
        - quality_level: 품질 등급 (excellent/good/fair/poor/critical)
        - checks: 개별 검사 결과
        - recommendations: 개선 권장사항
    """
    from mcp_server.tools.data_validator import validate_and_clean

    result = validate_and_clean(ticker, period, auto_clean=False)
    return result


@mcp.tool()
async def data_validate_and_clean(ticker: str, period: str = "1y") -> Dict:
    """데이터 검증 및 자동 정제

    데이터 품질 검증 후 문제가 있으면 자동으로 정제

    정제 항목:
    - 누락값: 전일 종가로 보간
    - 0값: 보간 처리
    - 이상치: 윈저화 (3σ 클리핑)

    Args:
        ticker: 종목 심볼
        period: 기간

    Returns:
        - validation: 정제 전 검증 결과
        - cleaning: 정제 내역
        - validation_after_clean: 정제 후 검증 결과
        - quality_improved: 품질 개선 여부
    """
    from mcp_server.tools.data_validator import validate_and_clean

    return validate_and_clean(ticker, period, auto_clean=True)


@mcp.tool()
async def data_quality_summary(tickers_csv: str, period: str = "1y") -> Dict:
    """여러 종목 데이터 품질 요약

    Args:
        tickers_csv: 쉼표로 구분된 티커 목록
        period: 기간

    Returns:
        - tickers: 종목별 품질 점수
        - summary: 전체 요약 (평균 점수, 등급별 개수)
    """
    from mcp_server.tools.data_validator import get_data_quality_summary

    tickers = [t.strip() for t in tickers_csv.split(",")]
    return get_data_quality_summary(tickers, period)


@mcp.tool()
async def data_clean(
    ticker: str,
    period: str = "1y",
    fill_missing: bool = True,
    remove_zeros: bool = True,
    winsorize: bool = True
) -> Dict:
    """데이터 정제 (수동)

    Args:
        ticker: 종목 심볼
        period: 기간
        fill_missing: 누락값 보간
        remove_zeros: 0값 처리
        winsorize: 이상치 윈저화

    Returns:
        - original_rows: 원본 행 수
        - filled_missing: 보간된 누락값 수
        - removed_zeros: 처리된 0값 수
        - winsorized: 윈저화된 이상치 수
    """
    from mcp_server.tools.data_validator import clean_price_data
    import yfinance as yf

    try:
        data = normalize_yf_columns(yf.download(ticker, period=period, progress=False))
        if data.empty:
            return {"error": f"No data for {ticker}"}
        data = data.reset_index()
    except Exception as e:
        return {"error": str(e)}

    cleaned, changes = clean_price_data(
        data,
        fill_missing=fill_missing,
        remove_zeros=remove_zeros,
        winsorize_outliers=winsorize
    )

    return {
        "ticker": ticker,
        "period": period,
        "changes": changes,
        "cleaned_rows": len(cleaned)
    }


@mcp.tool()
async def data_check_outliers(ticker: str, period: str = "1y", threshold: float = 3.0) -> Dict:
    """이상치 탐지

    Args:
        ticker: 종목 심볼
        period: 기간
        threshold: 이상치 임계값 (σ, 기본 3.0)

    Returns:
        - outlier_count: 이상치 개수
        - outliers: 이상치 목록 (날짜, 수익률)
        - statistics: 수익률 통계
    """
    import yfinance as yf
    import numpy as np

    try:
        data = normalize_yf_columns(yf.download(ticker, period=period, progress=False))
        if data.empty:
            return {"error": f"No data for {ticker}"}
    except Exception as e:
        return {"error": str(e)}

    close = data["Close"]
    returns = close.pct_change().dropna()

    mean = returns.mean()
    std = returns.std()

    if std == 0:
        return {"ticker": ticker, "outlier_count": 0, "message": "변동성이 없습니다."}

    z_scores = (returns - mean) / std
    outlier_mask = abs(z_scores) > threshold
    outliers = returns[outlier_mask]

    outlier_list = []
    for date, ret in outliers.items():
        outlier_list.append({
            "date": str(date.date()) if hasattr(date, 'date') else str(date),
            "return_pct": round(float(ret) * 100, 2),
            "z_score": round(float(z_scores[date]), 2)
        })

    return {
        "ticker": ticker,
        "period": period,
        "threshold": threshold,
        "outlier_count": len(outliers),
        "outliers": outlier_list[:20],  # 최대 20개
        "statistics": {
            "mean_return": round(float(mean) * 100, 4),
            "std_return": round(float(std) * 100, 4),
            "max_return": round(float(returns.max()) * 100, 2),
            "min_return": round(float(returns.min()) * 100, 2)
        }
    }


@mcp.tool()
async def data_check_missing(ticker: str, period: str = "1y") -> Dict:
    """누락 데이터 검사

    Args:
        ticker: 종목 심볼
        period: 기간

    Returns:
        - missing_count: 누락 데이터 개수
        - missing_pct: 누락 비율
        - by_column: 컬럼별 누락 개수
    """
    import yfinance as yf

    try:
        data = normalize_yf_columns(yf.download(ticker, period=period, progress=False))
        if data.empty:
            return {"error": f"No data for {ticker}"}
    except Exception as e:
        return {"error": str(e)}

    price_cols = ["Open", "High", "Low", "Close", "Volume"]
    cols_to_check = [c for c in price_cols if c in data.columns]

    missing_by_col = data[cols_to_check].isna().sum().to_dict()
    total_missing = sum(missing_by_col.values())
    total_cells = len(data) * len(cols_to_check)
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0

    # 누락 데이터가 있는 날짜 찾기
    missing_dates = []
    for idx, row in data[cols_to_check].iterrows():
        if row.isna().any():
            missing_dates.append({
                "date": str(idx.date()) if hasattr(idx, 'date') else str(idx),
                "missing_cols": [c for c in cols_to_check if pd.isna(row[c])]
            })

    return {
        "ticker": ticker,
        "period": period,
        "total_rows": len(data),
        "missing_count": int(total_missing),
        "missing_pct": round(missing_pct, 2),
        "by_column": {k: int(v) for k, v in missing_by_col.items()},
        "missing_dates": missing_dates[:20]  # 최대 20개
    }


# === Technical Analysis Tools (Phase 1-3) ===
from mcp_server.tools.technical_indicators import TechnicalFactors, calculate_technical_score

@mcp.tool()
async def technical_analyze(ticker: str, market: str = "US", period: str = "6mo") -> Dict:
    """기술적 분석 (10개 지표)

    Args:
        ticker: 종목 코드
        market: 시장 구분 ("US", "KR")
        period: 분석 기간 (6mo, 1y 등)

    Returns:
        - indicators: 10개 기술적 지표 값
        - interpretation: 지표 해석
        - score: 종합 스코어 (0-100)

    Examples:
        - 미국 주식: technical_analyze("AAPL", market="US")
        - 한국 주식: technical_analyze("005930", market="KR")
    """
    try:
        # 가격 데이터 조회
        df = get_prices(ticker, market=market)

        if df.empty:
            return {"error": f"No data for {ticker}"}

        # 기술적 지표 계산
        indicators = TechnicalFactors.calculate_all(df)

        if not indicators:
            return {"error": "Failed to calculate technical indicators"}

        # 해석
        interpretation = TechnicalFactors.get_factor_interpretation(indicators)

        # 종합 스코어
        score = calculate_technical_score(df)

        return {
            "ticker": ticker,
            "market": market,
            "indicators": indicators,
            "interpretation": interpretation,
            "score": round(score, 2),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Technical analysis failed for {ticker}: {e}")
        return {"error": str(e)}


@mcp.tool()
async def technical_compare(tickers: List[str], market: str = "US") -> List[Dict]:
    """여러 종목의 기술적 지표 비교

    Args:
        tickers: 종목 코드 리스트
        market: 시장 구분

    Returns:
        각 종목의 기술적 분석 결과 리스트

    Example:
        - technical_compare(["AAPL", "MSFT", "GOOGL"], market="US")
        - technical_compare(["005930", "035420"], market="KR")
    """
    results = []

    for ticker in tickers:
        result = await technical_analyze(ticker, market=market)
        results.append(result)

    return results


# ============================================================
# Phase 2: 재무 팩터 분석 도구
# ============================================================
@mcp.tool()
async def financial_analyze(ticker: str, market: str = "US") -> Dict:
    """재무 팩터 분석 (20개)

    Phase 2-1: 재무 지표 확장
    - 수익성 (5개): ROE, ROA, ROIC, Operating/Net Margin
    - 재무 건전성 (5개): Debt Ratios, Current/Quick Ratio, Interest Coverage
    - 효율성 (5개): Asset/Inventory/Receivables Turnover, FCF
    - 배당 (3개): Dividend Yield, Payout Ratio, Dividend Growth
    - 성장성 (2개): Revenue/EPS Growth

    Args:
        ticker: 종목 코드 (예: "AAPL", "005930")
        market: 시장 구분 ("US", "KR")

    Returns:
        {
            "ticker": "AAPL",
            "market": "US",
            "factors": {
                "ROE": 0.45,
                "ROA": 0.28,
                ...
            },
            "interpretation": {
                "ROE": "우수한 자기자본 수익률 (45.0%)",
                ...
            },
            "count": 10
        }

    Examples:
        - 미국 주식: financial_analyze("AAPL", market="US")
        - 한국 주식: financial_analyze("005930", market="KR")
    """
    try:
        from mcp_server.tools.financial_factors import FinancialFactors

        # 재무 팩터 계산
        factors = FinancialFactors.calculate_all(ticker, market)

        # 해석 생성
        interpretation = FinancialFactors.get_factor_interpretation(factors)

        return {
            "ticker": ticker,
            "market": market,
            "factors": factors,
            "interpretation": interpretation,
            "count": len(factors)
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "market": market}


@mcp.tool()
async def sentiment_analyze(ticker: str, market: str = "US", days: int = 7) -> Dict:
    """감성 분석 (10개)

    Phase 2-2: 감성 분석 팩터
    - 뉴스 감성 (3개): News Sentiment, News Volume, News Sentiment Std
    - 공시 분석 (2개): Filing Sentiment, Filing Frequency
    - 시장 심리 (3개): Put/Call Ratio, Market VIX, Short Interest Ratio
    - 전문가 의견 (2개): Analyst Rating, Target Price Upside

    Args:
        ticker: 종목 코드 (예: "AAPL", "005930")
        market: 시장 구분 ("US", "KR")
        days: 뉴스 분석 기간 (일)

    Returns:
        {
            "ticker": "AAPL",
            "market": "US",
            "factors": {
                "News_Sentiment": 0.35,
                "Put_Call_Ratio": 0.82,
                ...
            },
            "interpretation": {
                "News_Sentiment": "긍정적 뉴스 우세 (Bullish)",
                ...
            },
            "sentiment_score": 68.3,
            "count": 8
        }

    Examples:
        - sentiment_analyze("AAPL", market="US")
        - sentiment_analyze("005930", market="KR", days=14)
    """
    try:
        from mcp_server.tools.sentiment_analysis import SentimentFactors, calculate_sentiment_score

        # 감성 팩터 계산
        factors = SentimentFactors.calculate_all(ticker, market, days)

        # 해석 생성
        interpretation = SentimentFactors.get_factor_interpretation(factors)

        # 종합 스코어
        sentiment_score = calculate_sentiment_score(factors)

        return {
            "ticker": ticker,
            "market": market,
            "factors": factors,
            "interpretation": interpretation,
            "sentiment_score": round(sentiment_score, 2),
            "count": len(factors)
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker, "market": market}


@mcp.tool()
async def comprehensive_analyze(
    ticker: str,
    market: str = "US",
    include_technical: bool = True,
    include_financial: bool = True,
    include_sentiment: bool = True
) -> Dict:
    """종합 분석 (최대 46개 팩터)

    Phase 1 + Phase 2 통합 분석
    - 기술적 지표 (10개): RSI, MACD, ADX, etc. [Phase 1]
    - 재무 지표 (20개): ROE, ROA, Debt Ratios, etc. [Phase 2-1]
    - 감성 지표 (10개): News Sentiment, Analyst Rating, etc. [Phase 2-2]

    Args:
        ticker: 종목 코드
        market: 시장 구분 ("US", "KR")
        include_technical: 기술적 분석 포함
        include_financial: 재무 분석 포함
        include_sentiment: 감성 분석 포함

    Returns:
        {
            "ticker": "AAPL",
            "market": "US",
            "timestamp": "2026-02-27T14:00:00Z",
            "factors": {
                "technical": {...},  # 10개
                "financial": {...},  # 20개
                "sentiment": {...}   # 10개
            },
            "interpretation": {...},
            "composite_score": 75.8,
            "recommendation": "Buy"
        }

    Examples:
        - comprehensive_analyze("AAPL", market="US")
        - comprehensive_analyze("005930", market="KR", include_technical=False)
    """
    try:
        from datetime import datetime
        from mcp_server.tools.technical_indicators import TechnicalFactors
        from mcp_server.tools.financial_factors import FinancialFactors
        from mcp_server.tools.sentiment_analysis import SentimentFactors, calculate_sentiment_score
        from mcp_server.tools.market_data import get_prices

        all_factors = {}
        interpretation = {}

        # 1. 기술적 지표 (10개)
        if include_technical:
            try:
                df = get_prices(ticker, market=market, period="6mo")
                if not df.empty:
                    tech_factors = TechnicalFactors.calculate_all(df)
                    all_factors['technical'] = tech_factors

                    tech_interp = TechnicalFactors.get_factor_interpretation(tech_factors)
                    interpretation.update(tech_interp)
            except Exception as e:
                logger.warning(f"Technical analysis failed: {e}")

        # 2. 재무 지표 (20개)
        if include_financial:
            try:
                fin_factors = FinancialFactors.calculate_all(ticker, market)
                all_factors['financial'] = fin_factors

                fin_interp = FinancialFactors.get_factor_interpretation(fin_factors)
                interpretation.update(fin_interp)
            except Exception as e:
                logger.warning(f"Financial analysis failed: {e}")

        # 3. 감성 지표 (10개)
        if include_sentiment:
            try:
                sent_factors = SentimentFactors.calculate_all(ticker, market)
                all_factors['sentiment'] = sent_factors

                sent_interp = SentimentFactors.get_factor_interpretation(sent_factors)
                interpretation.update(sent_interp)
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")

        # 종합 스코어 계산 (간단한 평균)
        all_factor_values = []
        for category in all_factors.values():
            all_factor_values.extend(category.values())

        if all_factor_values:
            # 정규화 후 평균 (간단한 구현)
            composite_score = 50.0  # 기본값
            try:
                # 기술적 스코어
                if 'technical' in all_factors and all_factors['technical']:
                    from mcp_server.tools.technical_indicators import calculate_technical_score
                    tech_score = calculate_technical_score(df) if not df.empty else 50
                else:
                    tech_score = 50

                # 감성 스코어
                if 'sentiment' in all_factors:
                    sent_score = calculate_sentiment_score(all_factors['sentiment'])
                else:
                    sent_score = 50

                # 재무 스코어 (간단히 50으로 설정, 추후 개선)
                fin_score = 50

                composite_score = (tech_score + sent_score + fin_score) / 3
            except Exception:
                composite_score = 50.0
        else:
            composite_score = 50.0

        # 추천 등급
        if composite_score >= 70:
            recommendation = "Strong Buy"
        elif composite_score >= 60:
            recommendation = "Buy"
        elif composite_score >= 40:
            recommendation = "Hold"
        elif composite_score >= 30:
            recommendation = "Sell"
        else:
            recommendation = "Strong Sell"

        # 팩터 개수 계산
        total_count = sum(len(factors) for factors in all_factors.values())

        return {
            "ticker": ticker,
            "market": market,
            "timestamp": datetime.now().isoformat(),
            "factors": all_factors,
            "interpretation": interpretation,
            "composite_score": round(composite_score, 2),
            "recommendation": recommendation,
            "total_factors": total_count
        }

    except Exception as e:
        return {"error": str(e), "ticker": ticker, "market": market}


# ============================================================
# Phase 2 Week 4: 백테스트 및 팩터 통합 (Backtest + Factor Aggregation)
# ============================================================

@mcp.tool()
async def backtest_strategy(
    ticker: str,
    market: str = "US",
    start_date: str = "2023-01-01",
    end_date: str = "2024-12-31",
    rebalance_period: int = 30,
    buy_threshold: float = 60.0,
    sell_threshold: float = 40.0,
    initial_capital: float = 10000.0
) -> Dict:
    """팩터 기반 백테스트 실행

    Phase 2 Week 4 기능: 팩터 점수 기반 매매 전략 백테스트

    Args:
        ticker: 종목 코드
        market: 시장 구분 ("US", "KR")
        start_date: 시작일 (YYYY-MM-DD)
        end_date: 종료일 (YYYY-MM-DD)
        rebalance_period: 리밸런싱 주기 (일)
        buy_threshold: 매수 임계값 (팩터 점수 0-100)
        sell_threshold: 매도 임계값
        initial_capital: 초기 자본

    Returns:
        {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 10000,
            "final_value": 12500,
            "total_return": 25.0,
            "performance": {
                "CAGR": 23.5,
                "Total_Return": 25.0,
                "Max_Drawdown": 15.2,
                "Sharpe_Ratio": 1.35,
                "Win_Rate": 65.0,
                "Total_Trades": 12
            },
            "benchmark": {
                "benchmark_ticker": "SPY",
                "benchmark_return": 18.5,
                "excess_return": 6.5,
                "outperformance": true
            },
            "trades": [...]
        }

    Examples:
        - backtest_strategy("AAPL", market="US", start_date="2023-01-01")
        - backtest_strategy("005930", market="KR", rebalance_period=60)
    """
    try:
        from mcp_server.tools.backtest_engine import BacktestEngine

        result = BacktestEngine.run_backtest(
            ticker=ticker,
            market=market,
            start_date=start_date,
            end_date=end_date,
            rebalance_period=rebalance_period,
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            initial_capital=initial_capital
        )

        return result

    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        return {
            "error": str(e),
            "ticker": ticker,
            "market": market
        }


@mcp.tool()
async def rank_stocks(
    tickers_csv: str,
    market: str = "US",
    include_technical: bool = True,
    include_financial: bool = True,
    include_sentiment: bool = True
) -> List[Dict]:
    """다종목 팩터 기반 랭킹

    Phase 2 Week 4 기능: 여러 종목을 팩터 점수로 비교 및 랭킹

    Args:
        tickers_csv: 종목 코드 (쉼표 구분, 예: "AAPL,MSFT,GOOGL")
        market: 시장 구분 ("US", "KR")
        include_technical: 기술적 팩터 포함
        include_financial: 재무 팩터 포함
        include_sentiment: 감성 팩터 포함

    Returns:
        [
            {
                "rank": 1,
                "ticker": "AAPL",
                "composite_score": 78.5,
                "factor_count": 35,
                "recommendation": "Buy"
            },
            ...
        ]

    Examples:
        - rank_stocks("AAPL,MSFT,GOOGL", market="US")
        - rank_stocks("005930,000660,035420", market="KR", include_sentiment=False)
    """
    try:
        from mcp_server.tools.factor_aggregator import FactorAggregator

        tickers = [t.strip() for t in tickers_csv.split(',') if t.strip()]

        if not tickers:
            return {"error": "No valid tickers provided"}

        results = FactorAggregator.rank_stocks(
            tickers=tickers,
            market=market,
            include_technical=include_technical,
            include_financial=include_financial,
            include_sentiment=include_sentiment
        )

        # 추천 등급 추가
        for result in results:
            if 'composite_score' in result:
                result['recommendation'] = FactorAggregator.get_recommendation(result['composite_score'])

        return results

    except Exception as e:
        logger.error(f"Stock ranking failed: {e}")
        return [{"error": str(e)}]


@mcp.tool()
async def theme_analyze_with_factors(
    theme: str,
    top_n: int = 5,
    include_backtest: bool = False,
    include_sentiment: bool = True,
    rerank_by_backtest: bool = False,
    market: str = "US",
    backtest_start: str = "2024-01-01",
    backtest_end: str = "2024-12-31",
    factor_weights: Optional[Dict[str, float]] = None
) -> Dict:
    """테마 기반 종합 투자 분석

    Phase 3 Week 1-2 기능: 테마를 입력하면 관련 종목을 발굴하고, 40개 팩터 기반으로 랭킹한 후,
    선택적으로 백테스트를 실행하여 투자 의견을 제공합니다.

    Week 2 추가: 백테스트 성과 기반 재정렬 기능
    개선: factor_weights 파라미터 노출로 팩터 가중치 커스터마이징 가능

    Args:
        theme: 테마 키워드 (예: "AI", "semiconductor", "biotech")
        top_n: 반환할 상위 종목 수 (기본: 5)
        include_backtest: 백테스트 실행 여부 (기본: False)
        include_sentiment: 테마 감성 분석 포함 여부 (기본: True)
        rerank_by_backtest: 백테스트 성과 기반 재정렬 (Week 2, 기본: False)
        market: 시장 (US/KR, 기본: US)
        backtest_start: 백테스트 시작일 (YYYY-MM-DD, 기본: 2024-01-01)
        backtest_end: 백테스트 종료일 (YYYY-MM-DD, 기본: 2024-12-31)
        factor_weights: 팩터 가중치 커스터마이징 (예: {"financial": 0.5, "technical": 0.3, "sentiment": 0.2})

    Returns:
        테마 분석 결과:
        {
            "theme": "AI",
            "market": "US",
            "total_candidates": 15,
            "analyzed_stocks": 12,
            "top_n": 5,
            "top_stocks": [
                {
                    "ticker": "NVDA",
                    "rank": 1,
                    "composite_score": 85.2,
                    "factor_count": 38,
                    "recommendation": "Strong Buy",
                    "backtest": {
                        "total_return": 52.3,
                        "cagr": 45.2,
                        "max_drawdown": -18.5,
                        "sharpe_ratio": 2.1,
                        "win_rate": 65.0,
                        "trade_count": 8
                    }
                },
                ...
            ],
            "theme_sentiment": {
                "sentiment_score": 0.68,
                "sentiment_label": "Bullish",
                "news_volume": 150,
                "trending": true
            },
            "recommendation": "✅ 'AI' theme is trending with bullish sentiment | ..."
        }

    Examples:
        - theme_analyze_with_factors("AI", top_n=5)
        - theme_analyze_with_factors("semiconductor", top_n=3, include_backtest=True)
        - theme_analyze_with_factors("반도체", market="KR", top_n=5)
    """
    try:
        from mcp_server.tools.theme_factor_integrator import ThemeFactorIntegrator

        result = ThemeFactorIntegrator.analyze_theme(
            theme=theme,
            top_n=top_n,
            include_backtest=include_backtest,
            include_sentiment=include_sentiment,
            rerank_by_backtest=rerank_by_backtest,
            market=market,
            backtest_start=backtest_start,
            backtest_end=backtest_end,
            factor_weights=factor_weights
        )

        return result

    except Exception as e:
        logger.error(f"theme_analyze_with_factors failed: {e}")
        return {
            'error': str(e),
            'theme': theme
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
