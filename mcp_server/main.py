from __future__ import annotations
import json
from datetime import datetime
from mcp_server.tools.market_data import get_prices
from mcp_server.tools.news_search import search_news
from mcp_server.tools.analytics import rank_candidates
from mcp_server.tools.portfolio import evaluate_holdings
from mcp_server.tools.reports import generate_report
from mcp_server.tools.obsidian import write_markdown
from mcp_server.tools.filings import fetch_recent_filings, summarize_filings_items
from mcp_server.tools.llm import summarize_items_perplexity


def main():
    tickers = ["AAPL", "MSFT", "NVDA"]

    # News (Perplexity 우선, 실패 시 RSS)
    news = search_news(["AI chips", "cloud growth"], lookback_days=7, max_results=3)
    news_lines = []
    for n in news:
        for h in n.get("hits", [])[:3]:
            news_lines.append(f"{h.get('title')} | {h.get('source')} | {h.get('url')}")
    news_summary = summarize_items_perplexity(news_lines, max_sentences=6) if news_lines else ""

    # SEC Filings
    filings_all = []
    for t in tickers:
        filings_all.extend(fetch_recent_filings(t, forms=["8-K", "10-Q", "10-K"], limit=3))
    filings_summary = summarize_filings_items(filings_all, max_items=6)

    # Ranking with dip bonus
    candidates = [
        {"ticker": "AAPL", "growth": 0.3, "profitability": 0.4, "valuation": 0.2, "quality": 0.6},
        {"ticker": "MSFT", "growth": 0.5, "profitability": 0.5, "valuation": 0.3, "quality": 0.7},
        {"ticker": "NVDA", "growth": 0.8, "profitability": 0.6, "valuation": 0.2, "quality": 0.6},
    ]
    ranked = rank_candidates(candidates, dip_weight=0.12, use_dip_bonus=True)

    payload = {
        "title": "Weekly Theme Snapshot",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tickers": tickers,
        "summary": "Condensed view with news and SEC filings summaries.",
        "news_summary": news_summary,
        "filings_summary": filings_summary,
        "scores": ranked,
    }
    md = generate_report(payload)
    path = write_markdown(
        "Markets/AI/Weekly Snapshot.md",
        front_matter={"type": "market", "date": payload["date"], "queries": [n["query"] for n in news]},
        body=md,
    )

    print(json.dumps({
        "news_items": len(news_lines),
        "filings_items": len(filings_all),
        "top_score": ranked[0],
        "report_path": path
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
