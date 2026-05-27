"""Request-scoped structured logging.

FR-B12: Unified structured logging with request_id context.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(value: str | None = None) -> str:
    rid = value or uuid.uuid4().hex[:12]
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id_var.get()


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        record.request_id = _request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    fmt = "%(asctime)s %(levelname)s [rid=%(request_id)s] %(name)s: %(message)s"
    handler.setFormatter(logging.Formatter(fmt))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
