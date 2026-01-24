from __future__ import annotations
from typing import List, Dict
from datetime import datetime, timedelta
import os
import json
import hashlib
import urllib.parse as urlparse
import logging
import feedparser
import requests

from mcp_server.tools.cache_manager import cache_manager, TTL
from mcp_server.tools.resilience import (
    retry_with_backoff, Timeout, RetryConfig,
    circuit_perplexity, circuit_rss, CircuitOpenError,
    FallbackChain
)

logger = logging.getLogger(__name__)


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


def _fetch_rss_feed(url: str) -> dict:
    """RSS 피드 조회 (서킷 브레이커 + 타임아웃)"""
    try:
        return circuit_rss.call(
            lambda: feedparser.parse(url, request_headers={"User-Agent": "PM-MCP/1.0"})
        )
    except CircuitOpenError:
        logger.warning(f"RSS circuit open, skipping: {url}")
        return {"entries": []}
    except Exception as e:
        logger.warning(f"RSS fetch error: {e}")
        return {"entries": []}


def _search_news_rss(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    out: List[Dict] = []
    cutoff = _now_utc() - timedelta(days=lookback_days)
    for q in queries:
        q_enc = urlparse.quote(q)
        rss_url = f"https://news.google.com/rss/search?q={q_enc}&hl=en-US&gl=US&ceid=US:en"
        feed = _fetch_rss_feed(rss_url)
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


@retry_with_backoff(
    attempts=RetryConfig.PERPLEXITY["attempts"],
    min_wait=RetryConfig.PERPLEXITY["min_wait"],
    max_wait=RetryConfig.PERPLEXITY["max_wait"]
)
def _call_perplexity_api(url: str, headers: dict, payload: dict) -> dict:
    """Perplexity API 호출 (재시도 + 서킷 브레이커)"""
    def _do_request():
        resp = requests.post(
            url, headers=headers,
            data=json.dumps(payload),
            timeout=Timeout.PERPLEXITY
        )
        resp.raise_for_status()
        return resp.json()

    return circuit_perplexity.call(_do_request)


def _search_news_perplexity(queries: List[str], lookback_days: int = 7, max_results: int = 10) -> List[Dict]:
    """Perplexity Chat Completions API를 이용해 뉴스 요약과 링크를 JSON으로 수신.
    - 모델: pplx-70b-online(또는 sonar-small-online 등)
    - 응답 파싱 실패 시 RSS로 폴백
    - 재시도 + 서킷 브레이커 적용
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
            j = _call_perplexity_api(url, headers, payload)
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
            logger.debug(f"Perplexity search success: {q} ({len(hits)} hits)")
        except CircuitOpenError:
            logger.warning(f"Perplexity circuit open, falling back to RSS: {q}")
            out.extend(_search_news_rss([q], lookback_days=lookback_days, max_results=max_results))
        except Exception as e:
            # Perplexity 실패 시 해당 쿼리는 RSS로 폴백
            logger.warning(f"Perplexity failed for '{q}': {type(e).__name__}: {e}, falling back to RSS")
            out.extend(_search_news_rss([q], lookback_days=lookback_days, max_results=max_results))
    return out


def search_news(queries: List[str], lookback_days: int = 7, max_results: int = 10, use_cache: bool = True) -> List[Dict]:
    """뉴스 검색(Perplexity 우선, 실패 시 RSS 폴백). 1시간 캐시 적용.
    반환 스키마: [{ query, hits: [{title, url, published, source, snippet}] }]
    """
    # 캐시 키 생성
    if use_cache:
        key_data = json.dumps({"queries": sorted(queries), "lookback": lookback_days, "max": max_results}, sort_keys=True)
        cache_key = f"news:{hashlib.md5(key_data.encode()).hexdigest()[:12]}"
        cached_result = cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result

    # 뉴스 검색 실행
    result = None
    if os.getenv("PERPLEXITY_API_KEY"):
        try:
            result = _search_news_perplexity(queries, lookback_days=lookback_days, max_results=max_results)
        except Exception:
            pass

    if result is None:
        result = _search_news_rss(queries, lookback_days=lookback_days, max_results=max_results)

    # 결과 캐싱
    if use_cache and result:
        cache_manager.set(cache_key, result, TTL.NEWS)

    return result
