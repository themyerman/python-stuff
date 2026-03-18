"""Structured logging helpers with correlation ID in context."""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("ascp_correlation_id", default=None)


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        cid = _correlation_id.get()
        record.correlation_id = cid if cid is not None else "-"
        return True


def configure_logging(
    level: str | int = "INFO",
    *,
    fmt: str | None = None,
) -> None:
    """Configure root logging with correlation_id on every record."""
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    fmt = fmt or "%(asctime)s %(levelname)s [%(name)s] [correlation_id=%(correlation_id)s] %(message)s"
    root = logging.getLogger()
    root.setLevel(level)
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.addFilter(_CorrelationIdFilter())
    handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def bind_correlation_id(correlation_id: str | None) -> Any:
    """
    Set correlation ID for the current async/task context.
    Returns a token for reset_correlation_id(token) if needed.
    """
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Any) -> None:
    _correlation_id.reset(token)
