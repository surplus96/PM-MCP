from __future__ import annotations
from typing import Iterator, List
import os, logging, time, requests

from mcp_server.tools.resilience import (
    retry_with_backoff, Timeout, RetryConfig, circuit_gemini, CircuitOpenError
)

logger = logging.getLogger(__name__)

# Google AI Studio (Gemma 4) — FR-B02: API key via header, FR-B14: GEMINI_MODEL naming
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Prefer canonical GEMINI_MODEL; fall back to legacy GEMMA_MODEL for backward compatibility
GEMINI_MODEL = os.getenv("GEMINI_MODEL", os.getenv("GEMMA_MODEL", "gemini-3.1-flash-lite-preview"))
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def _auth_headers() -> dict[str, str]:
    """Build headers with Gemini API key (header-based, never in URL).

    FR-B02: Secret never in URL query string or logs.
    """
    return {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY,
    }


# Default output budget. Korean Markdown reports were getting truncated at
# ~2048 tokens because Korean glyphs cost ~1.5-3 tokens per character. 8192
# is well within Gemini 2.0/2.5 Flash limits and absorbs typical analysis
# reports without cutting mid-sentence. Chat callers can lower this with
# the ``max_output_tokens`` argument when they want a leaner reply.
LLM_MAX_OUTPUT_TOKENS_DEFAULT = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "8192"))


def _call_gemma_no_retry(
    system: str,
    user: str,
    temperature: float = 0.2,
    *,
    model: str | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """Single-shot Gemini API call without ``retry_with_backoff`` wrapping.

    Used by ``call_llm_resilient`` so the smart retry / fallback policy
    isn't double-counted with the tenacity-driven retries on the public
    ``_call_gemma`` (which would otherwise burn quota faster on 429s).
    Direct callers should keep using ``_call_gemma`` for backward compat.

    A ``finishReason`` of ``MAX_TOKENS`` is logged as a warning — that is
    almost always why a downstream Markdown report shows up mid-sentence.
    """
    use_model = model or GEMINI_MODEL
    url = f"{GEMINI_BASE_URL}/models/{use_model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens or LLM_MAX_OUTPUT_TOKENS_DEFAULT,
        },
    }

    def _do_request():
        resp = requests.post(
            url,
            json=payload,
            headers=_auth_headers(),
            timeout=Timeout.GEMINI,
        )
        resp.raise_for_status()
        # Force UTF-8 — Gemini's Content-Type sometimes omits the
        # charset, which makes ``requests`` fall back to ISO-8859-1
        # via apparent_encoding. ``resp.json()`` then decodes Korean
        # 3-byte sequences as Latin-1 chars and the answer comes out
        # as ``ì¼ì±ì ì`` mojibake. Pinning encoding fixes the chat +
        # analysis-report Korean output in a single line.
        resp.encoding = "utf-8"
        return resp.json()

    result = circuit_gemini.call(_do_request)
    candidates = result.get("candidates", [])
    if not candidates:
        return ""
    cand = candidates[0]
    finish = cand.get("finishReason", "")
    if finish == "MAX_TOKENS":
        # Surfacing this so an operator notices systematic truncation —
        # bump LLM_MAX_OUTPUT_TOKENS env or pass max_output_tokens=...
        logger.warning(
            "LLM response truncated by maxOutputTokens (model=%s, limit=%d). "
            "Increase LLM_MAX_OUTPUT_TOKENS or pass a larger max_output_tokens.",
            use_model, payload["generationConfig"]["maxOutputTokens"],
        )
    parts = cand.get("content", {}).get("parts", [])
    if parts:
        return parts[0].get("text", "").strip()
    return ""


@retry_with_backoff(
    attempts=RetryConfig.GEMINI["attempts"],
    min_wait=RetryConfig.GEMINI["min_wait"],
    max_wait=RetryConfig.GEMINI["max_wait"],
)
def _call_gemma(
    system: str,
    user: str,
    temperature: float = 0.2,
    *,
    model: str | None = None,
    max_output_tokens: int | None = None,
) -> str:
    """Google AI Studio API 호출 (Gemini / Gemma).

    - FR-B02: API key sent as ``x-goog-api-key`` header (not URL query).
    - FR-B03: Timeout honors ``Timeout.GEMINI`` (default 300s, env-overridable).
    - FR-B03: ``retry_with_backoff`` decorator applied on the low-level call itself.
    - FR-P01: ``model`` overrides the module-level ``GEMINI_MODEL`` per-call
      so the chatbot can pin itself to a stable model while other callers
      (analysis reports, summaries) keep their own default.
    """
    return _call_gemma_no_retry(
        system, user, temperature=temperature, model=model,
        max_output_tokens=max_output_tokens,
    )


# ---------------------------------------------------------------------------
# Resilient wrapper (FR-P05) — moved from api/services/chat_service.py so every
# caller (chat, streaming, future analysis routes) can share it.
# ---------------------------------------------------------------------------

_LLM_FALLBACK_MODELS_DEFAULT = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        # Live-probe verified chain (2026-04-23). Each entry returns 200 on
        # GET /v1beta/models/{name}. Order is newest → oldest stable so
        # quality degrades smoothly when the primary 503's. The previous
        # default included ``gemini-1.5-flash-latest`` and ``gemini-1.5-pro``
        # which both 404 on this API tier and just wasted a round-trip
        # before ``is_model_not_found_error`` skipped past them.
        "gemini-2.0-flash,gemini-2.0-flash-lite,gemini-2.5-flash-lite",
    ).split(",")
    if m.strip()
]
_LLM_INNER_RETRIES = int(os.getenv("LLM_INNER_RETRIES", "3"))
_LLM_RETRY_BACKOFF_SEC = float(os.getenv("LLM_RETRY_BACKOFF_SEC", "2.0"))


def is_transient_upstream_error(exc: BaseException) -> bool:
    """True for HTTP 5xx/429, timeouts, and connection issues."""
    msg = str(exc).lower()
    if any(t in msg for t in ("503", "502", "504", "500", "429",
                              "service unavailable", "timeout", "timed out",
                              "connection")):
        return True
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    return bool(code and (code >= 500 or code == 429))


def is_rate_limit_error(exc: BaseException) -> bool:
    """True only for HTTP 429 — distinct from generic transient 5xx.

    Rationale: 429 = quota exhausted, retrying the *same* model just burns
    more quota and trips the circuit breaker. Skip same-model retries and
    move straight to the next fallback when this is the failure shape.
    """
    msg = str(exc).lower()
    if "429" in msg or "too many requests" in msg or "quota" in msg:
        return True
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    return code == 429


def is_circuit_open_error(exc: BaseException) -> bool:
    """True when our local circuit breaker has tripped — same model is dead
    until the breaker half-opens; skip ahead to fallback immediately."""
    msg = str(exc).lower()
    return "circuit[" in msg and "open" in msg


def is_model_not_found_error(exc: BaseException) -> bool:
    """True when the upstream returns 404 for the model id — usually a typo
    or a deprecated name. Skip retries on this model; the next fallback
    might actually exist."""
    msg = str(exc).lower()
    if "404" in msg or "not found" in msg:
        return True
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    return code == 404


def call_llm_resilient(
    system: str,
    user: str,
    *,
    model: str | None = None,
    fallback_models: list[str] | None = None,
    temperature: float = 0.2,
    max_output_tokens: int | None = None,
) -> str:
    """Call Gemini with smart retry + model fallback chain.

    Strategy
        * 5xx / timeout / connection → retry the same model up to
          ``_LLM_INNER_RETRIES`` times with exponential backoff.
        * 429 (rate-limit / quota) → **do not** retry the same model;
          jump immediately to the next fallback. Retrying just burns
          more quota and trips the circuit breaker.
        * Local circuit open → same as 429: skip to next fallback.
        * Non-transient (auth, schema) → raise immediately.

    Note that ``_call_gemma`` itself already has a tenacity-based 2-attempt
    retry on HTTPError, so the *effective* attempts per model for 5xx is
    ``2 * (_LLM_INNER_RETRIES + 1)``. Keeping the inner loop low (default 3)
    is intentional — quota burns fast.
    """
    primary = model or GEMINI_MODEL
    chain = [primary, *[m for m in (fallback_models or _LLM_FALLBACK_MODELS_DEFAULT)
                        if m != primary]]
    last_exc: BaseException | None = None

    for m_idx, m in enumerate(chain):
        for attempt in range(_LLM_INNER_RETRIES + 1):
            try:
                # Use the *no-retry* primitive so we don't double-burn quota
                # via tenacity's inner retry loop on top of our outer one.
                result = _call_gemma_no_retry(
                    system, user, temperature=temperature, model=m,
                    max_output_tokens=max_output_tokens,
                )
                if m != primary:
                    logger.info("LLM fallback succeeded with %s (primary %s failing)",
                                m, primary)
                return result
            except Exception as e:  # noqa: BLE001
                last_exc = e
                # 404 model-not-found: skip this model entirely (don't
                # raise — the next fallback might be a valid id).
                if is_model_not_found_error(e):
                    logger.warning(
                        "LLM model %s does not exist (404) — skipping to next fallback",
                        m,
                    )
                    break
                if not is_transient_upstream_error(e):
                    raise
                # 429 / circuit-open: don't retry the same model. Also
                # proactively reset the circuit so the *next* model in the
                # chain isn't blocked by the breaker that primary tripped.
                if is_rate_limit_error(e) or is_circuit_open_error(e):
                    logger.warning(
                        "LLM %s blocked (%s) — skipping same-model retries, "
                        "advancing to next fallback",
                        m, "rate-limit" if is_rate_limit_error(e) else "circuit-open",
                    )
                    try:
                        circuit_gemini.reset()
                    except Exception:  # noqa: BLE001
                        pass
                    break
                wait = _LLM_RETRY_BACKOFF_SEC * (2 ** attempt)
                logger.warning(
                    "LLM %s attempt %d/%d failed (%s); retrying in %.1fs",
                    m, attempt + 1, _LLM_INNER_RETRIES + 1, e, wait,
                )
                time.sleep(wait)
        logger.warning("LLM model %s exhausted; trying next (%d/%d)",
                       m, m_idx + 1, len(chain))

    assert last_exc is not None
    raise last_exc


def call_llm_json(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.1,
) -> str:
    """Convenience wrapper used by ``rich-visual-reports`` (FR-R-B03).

    Lower temperature (0.1) nudges the model toward deterministic JSON
    output; callers parse via ``api.services.report_builder.parse_llm_blocks``
    which tolerates stray prose / code fences and degrades to a prose
    fallback so a single malformed response never breaks a report.
    """
    return call_llm_resilient(system, user, model=model, temperature=temperature)


def _call_gemma_stream(system: str, user: str, temperature: float = 0.2, *, model: str | None = None):
    """Streaming variant of ``_call_gemma``.

    Yields incremental text deltas by consuming Gemini's
    ``:streamGenerateContent?alt=sse`` endpoint. Resilience is deliberately
    *lighter* than ``_call_gemma`` because:

      * The chat stream service wraps this generator in its own try/except
        so a transient 5xx still yields a user-visible ``error`` event.
      * Retrying a long-running SSE stream mid-flight would duplicate text.

    If the upstream returns non-200 or an invalid stream, we fall back to
    one non-streaming call and yield its full text as a single chunk so
    the frontend still sees *something*.
    """
    use_model = model or GEMINI_MODEL
    url = f"{GEMINI_BASE_URL}/models/{use_model}:streamGenerateContent?alt=sse"
    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        },
    }
    try:
        with requests.post(
            url,
            json=payload,
            headers=_auth_headers(),
            timeout=Timeout.GEMINI,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            # Force UTF-8 before ``iter_lines(decode_unicode=True)`` —
            # Gemini's SSE response Content-Type doesn't always declare a
            # charset, so requests falls back to ISO-8859-1 and Korean
            # 3-byte sequences come out as ``ì¼ì±ì ì`` mojibake. The chat
            # streaming path is the high-traffic UI surface so this fix
            # matters most here.
            resp.encoding = "utf-8"
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if not raw.startswith("data: "):
                    continue
                blob = raw[len("data: "):].strip()
                if blob in ("[DONE]", ""):
                    continue
                try:
                    import json as _json
                    obj = _json.loads(blob)
                except Exception:  # noqa: BLE001
                    continue
                candidates = obj.get("candidates") or []
                if not candidates:
                    continue
                parts = (candidates[0].get("content") or {}).get("parts") or []
                for p in parts:
                    delta = p.get("text") or ""
                    if delta:
                        yield delta
    except Exception as e:  # noqa: BLE001
        logger.warning("stream call failed, falling back to non-streaming: %s", e)
        try:
            text = _call_gemma(system, user, temperature=temperature)
            if text:
                yield text
        except Exception as e2:  # noqa: BLE001
            # Re-raise so the chat stream service can emit an error event.
            raise e2 from e


def summarize_text(text: str, max_sentences: int = 6, model: str | None = None) -> str:
    """텍스트 요약 (Gemini via Google AI Studio).

    Routes through ``call_llm_resilient`` (FR-P05) so transient 503s on
    preview models retry + fall back through ``GEMINI_FALLBACK_MODELS``
    instead of bubbling a one-shot failure to filings / theme reports.
    """
    if not text or not text.strip():
        return ""

    system = (
        f"You are a concise financial analyst. Summarize in {max_sentences} sentences (bullet-ready). "
        "Focus on drivers, risks, guidance, and near-term catalysts."
    )
    try:
        return call_llm_resilient(system, text[:8000], model=model, temperature=0.2)
    except CircuitOpenError:
        logger.warning("Gemini circuit open, skipping summarization")
        return ""
    except Exception as e:  # noqa: BLE001 - narrow logging, no user-visible stack
        logger.warning("Gemini summarization failed: %s", e)
        return ""


def summarize_items(lines: List[str], max_sentences: int = 6) -> str:
    """리스트 항목 요약 (Gemma 4 via Google AI Studio)."""
    text = "\n".join(f"- {ln}" for ln in lines if ln)
    return summarize_text(text, max_sentences=max_sentences)
