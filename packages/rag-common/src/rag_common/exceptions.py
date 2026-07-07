from __future__ import annotations

from typing import Any


class RagBaseError(Exception):
    """Base exception for all RAG platform errors.

    All module-specific exceptions should inherit from this class
    (directly or via one of the shared subclasses below) so that
    callers up the stack can catch and handle by category uniformly.

    Attributes:
        message: Human-readable error description.
        context: Arbitrary key-value pairs for structured logging/debugging.
        retryable: Whether it is safe to retry the operation that failed.
    """

    def __init__(
        self,
        message: str = "",
        *,
        context: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        self.context = context or {}
        self.retryable = retryable
        super().__init__(message)

    @property
    def message(self) -> str:
        return self.args[0] if self.args else ""


class ConfigurationError(RagBaseError):
    """Raised when module configuration is missing or invalid.

    Always non-retryable — fix the config and restart.
    """

    def __init__(
        self,
        message: str = "",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context, retryable=False)


class RetryableError(RagBaseError):
    """Raised on transient failures that are safe to retry.

    Examples: network timeouts, rate limits, temporary provider outages.

    The caller should apply backoff before retrying.
    """

    def __init__(
        self,
        message: str = "",
        *,
        context: dict[str, Any] | None = None,
        retries_remaining: int = 0,
    ) -> None:
        self.retries_remaining = retries_remaining
        super().__init__(message, context=context, retryable=True)


class TerminalError(RagBaseError):
    """Raised when all retries/fallbacks have been exhausted.

    Requires human review — not safe to retry automatically.
    """

    def __init__(
        self,
        message: str = "",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context, retryable=False)


class ValidationError(RagBaseError):
    """Raised when input data fails schema or contract validation.

    Always non-retryable — fix the input and resubmit.
    """

    def __init__(
        self,
        message: str = "",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, context=context, retryable=False)
