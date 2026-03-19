"""Structured logging with correlation_id in context and log records."""

import logging
from contextvars import ContextVar

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def bind_correlation_id(correlation_id: str | None) -> None:
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get(None)


class CorrelationIdFilter(logging.Filter):
    """Add correlation_id to log record if set."""

    def filter(self, record: logging.LogRecord) -> bool:
        cid = get_correlation_id()
        setattr(record, "correlation_id", cid if cid else "")
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(
            logging.Formatter("%(levelname)s [%(name)s] %(correlation_id)s %(message)s")
        )
        h.addFilter(CorrelationIdFilter())
        root.addHandler(h)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
