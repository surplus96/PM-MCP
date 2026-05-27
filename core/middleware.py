"""Request-scoped middleware (request_id, timing)."""
from __future__ import annotations

import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from core.logging import get_logger, set_request_id

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a request_id to each inbound request and expose it via header."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        incoming = request.headers.get("x-request-id")
        rid = set_request_id(incoming)
        request.state.request_id = rid
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000
            logger.exception("request_failed path=%s ms=%.1f", request.url.path, elapsed)
            raise
        elapsed = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = rid
        logger.info(
            "request_ok method=%s path=%s status=%s ms=%.1f",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response
