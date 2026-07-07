from __future__ import annotations

import contextvars
import logging
import os
import sys
from typing import Any

import structlog

_log_context_var: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar(
    "_rag_log_context", default={}
)


def _add_correlation_fields(
    logger: structlog.stdlib.BoundLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    ctx = _log_context_var.get()
    if ctx:
        event_dict.update(ctx)
    return event_dict


_setup_complete: bool = False


def setup_logging() -> None:
    global _setup_complete

    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get("LOG_FORMAT", "json").lower()
    level = getattr(logging, log_level, logging.INFO)

    shared_processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_correlation_fields,
    ]

    if log_format == "console" or (log_format == "auto" and sys.stderr.isatty()):
        renderer: Any = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)

    _setup_complete = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name or __name__)
    return logger


class log_context:
    def __init__(self, **kwargs: str) -> None:
        self._kwargs = kwargs

    def __enter__(self) -> None:
        self._token = _log_context_var.set({**_log_context_var.get(), **self._kwargs})

    def __exit__(self, *args: Any) -> None:
        _log_context_var.reset(self._token)
