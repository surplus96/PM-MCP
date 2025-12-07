from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timedelta
import os
import json
import urllib.parse as urlparse
import feedparser
import requests


def _now_utc():
    return datetime.utcnow()


def _to_iso(dt):
    try:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def _parse_published(entry) -> datetime | None:
    try:
        # feedparser returns time.struct_time in published_parsed
        if getattr(entry, "published_parsed", None):
            import time
            return datetime.utcfromtimestamp(time.mktime(entry.published_parsed))
    except Exception:
        return None
    return None


def _search_news_rss(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    out: List[Dict] = []
    cutoff = _now_utc() - timedelta(days=lookback_days)
    for q in queries:
        q_enc = urlparse.quote(q)
        rss = f"https://news.google.com/rss/search?q={q_enc}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss)
        hits = []
        for e in getattr(feed, "entries", [])[: max_results * 2]:  # 여유 파싱 후 컷
            pub = _parse_published(e)
            if pub and pub < cutoff:
                continue
            hits.append({
                "title": getattr(e, "title", ""),
                "url": getattr(e, "link", ""),
                "published": _to_iso(pub) if pub else None,
                "source": getattr(getattr(e, "source", {}), "title", None) or getattr(e, "source", None),
                "snippet": getattr(e, "summary", "")[:300]
            })
            if len(hits) >= max_results:
                break
        out.append({"query": q, "hits": hits})
    return out


def _search_news_perplexity(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    """Perplexity Chat Completions API를 이용해 뉴스 요약과 링크를 JSON으로 수신.
    - 모델: pplx-70b-online(또는 sonar-small-online 등)
    - 응답 파싱 실패 시 RSS로 폴백
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise RuntimeError("PERPLEXITY_API_KEY is not set")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    model = os.getenv("PERPLEXITY_MODEL", "pplx-70b-online")

    out: List[Dict] = []
    cutoff_date = (_now_utc() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    system = (
        "You are a financial news assistant. Return ONLY valid JSON with an array of items: "
        "[{title, url, published, source, snippet}]. Use ISO8601 date for 'published'. "
        "Prefer recent items after " + cutoff_date + ". Max items: " + str(max_results) + "."
    )

    for q in queries:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Query: {q}. Return only JSON array without extra text."}
            ],
            "temperature": 0.2
        }
        try:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            resp.raise_for_status()
            j = resp.json()
            content = j.get("choices", [{}])[0].get("message", {}).get("content", "")
            # content가 JSON 배열이 아닐 경우 대괄호 구간만 추출해 재시도
            try:
                items = json.loads(content)
            except Exception:
                start = content.find('[')
                end = content.rfind(']')
                if start != -1 and end != -1 and end > start:
                    items = json.loads(content[start:end+1])
                else:
                    raise
            if not isinstance(items, list):
                raise ValueError("Perplexity returned non-list JSON")
            hits = []
            for it in items[:max_results]:
                hits.append({
                    "title": it.get("title"),
                    "url": it.get("url"),
                    "published": it.get("published"),
                    "source": it.get("source"),
                    "snippet": it.get("snippet")[:300] if isinstance(it.get("snippet"), str) else None,
                })
            out.append({"query": q, "hits": hits})
        except Exception:
            # Perplexity 실패 시 해당 쿼리는 RSS로 폴백
            out.extend(_search_news_rss([q], lookback_days=lookback_days, max_results=max_results))
    return out


def search_news(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    """뉴스 검색(Perplexity 우선, 실패 시 RSS 폴백).
    반환 스키마: [{ query, hits: [{title, url, published, source, snippet}] }]
    """
    if os.getenv("PERPLEXITY_API_KEY"):
        try:
            return _search_news_perplexity(queries, lookback_days=lookback_days, max_results=max_results)
        except Exception:
            pass
    return _search_news_rss(queries, lookback_days=lookback_days, max_results=max_results)
