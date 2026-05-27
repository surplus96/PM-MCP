"""Timezone-aware datetime helpers (FR-B23).

Rationale: naive `datetime.now()` is ambiguous across environments.
All timestamps emitted by the API must be UTC with tzinfo.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    """Return current time as tz-aware UTC datetime."""
    return datetime.now(tz=timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Attach/convert tzinfo to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def period_to_dates(period: str) -> tuple[str, str]:
    """Convert period string (e.g. '3mo', '1y') to ('YYYY-MM-DD', 'YYYY-MM-DD') in UTC."""
    end = utcnow()
    mapping = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730}
    days = mapping.get(period, 180)
    start = end - timedelta(days=days)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
