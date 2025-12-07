from __future__ import annotations
from typing import List
import os, json, requests

PPLX_URL = "https://api.perplexity.ai/chat/completions"


def summarize_text_perplexity(text: str, max_sentences: int = 6, model: str | None = None) -> str:
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return ""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    model = model or os.getenv("PERPLEXITY_MODEL", "pplx-70b-online")
    system = (
        f"You are a concise financial analyst. Summarize in {max_sentences} sentences (bullet-ready). "
        "Focus on drivers, risks, guidance, and near-term catalysts."
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text[:8000]},
        ],
        "temperature": 0.2,
    }
    try:
        resp = requests.post(PPLX_URL, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        j = resp.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except Exception:
        return ""


def summarize_items_perplexity(lines: List[str], max_sentences: int = 6) -> str:
    text = "\n".join(f"- {ln}" for ln in lines if ln)
    return summarize_text_perplexity(text, max_sentences=max_sentences)
