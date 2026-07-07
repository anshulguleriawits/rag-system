from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar

from rag_common.logging import get_logger

F = TypeVar("F", bound=Callable[..., Any])

_logger = get_logger(__name__)


def timed_operation(stage_name: str) -> Callable[[F], F]:
    """Decorator that logs operation start, completion (with duration), and errors.

    Logs at INFO on success, ERROR on failure. Structured so the body can be
    swapped later to emit real OpenTelemetry spans without changing call sites.

    Args:
        stage_name: Human-readable label for the operation
            (e.g. ``"parse_document"``, ``"chunk_document"``, ``"embed_chunk"``).
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _logger.info("Operation started", stage=stage_name)
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = int((time.monotonic() - start) * 1000)
                _logger.info(
                    "Operation completed",
                    stage=stage_name,
                    duration_ms=elapsed_ms,
                )
                return result
            except Exception as exc:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                _logger.error(
                    "Operation failed",
                    stage=stage_name,
                    duration_ms=elapsed_ms,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
