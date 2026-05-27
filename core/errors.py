"""Unified error types and FastAPI exception handlers.

FR-B06: Replace bare except with structured error handling.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.logging import get_request_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Application-level error with a stable error code."""

    http_status: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationAppError(AppError):
    http_status = 400
    code = "VALIDATION_ERROR"


class NotFoundError(AppError):
    http_status = 404
    code = "NOT_FOUND"


class UpstreamError(AppError):
    http_status = 502
    code = "UPSTREAM_ERROR"


class LLMTimeoutError(AppError):
    http_status = 504
    code = "LLM_TIMEOUT"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": get_request_id(),
            "details": details or {},
        }
    }


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:  # type: ignore[override]
        logger.warning("app_error code=%s msg=%s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[override]
        return JSONResponse(
            status_code=400,
            content=_error_body("VALIDATION_ERROR", "Invalid request", {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:  # type: ignore[override]
        code = {
            400: "BAD_REQUEST",
            401: "AUTH_REQUIRED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            429: "RATE_LIMITED",
        }.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def _fallback_handler(_: Request, exc: Exception) -> JSONResponse:  # type: ignore[override]
        logger.exception("unhandled_exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_error_body("INTERNAL_ERROR", "Internal server error"),
        )
