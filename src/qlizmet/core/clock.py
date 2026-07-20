"""Единый источник времени для ядра.

Вынесен отдельно, чтобы модели и алгоритмы могли принимать ``now`` явно и
тестироваться детерминированно, не завися от системных часов.
"""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Текущее время в UTC (timezone-aware)."""
    return datetime.now(timezone.utc)