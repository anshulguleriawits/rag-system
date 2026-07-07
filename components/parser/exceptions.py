from common import (
    RagBaseError,
    ConfigurationError as CommonConfigurationError,
    RetryableError,
    TerminalError,
)


class ParserError(RagBaseError):
    """Base exception for all parser module errors."""


class ParserNotFoundError(ParserError):
    """Raised when no matching parser strategy is found for a file."""


class ParsingTimeoutError(ParserError, RetryableError):
    """Raised when a parsing operation exceeds the configured timeout."""


class LowConfidenceParseError(ParserError):
    """Raised when parsed output confidence is below the acceptable threshold."""


class AllStrategiesFailedError(ParserError, TerminalError):
    """Raised when every strategy in the fallback chain failed for a document."""


class ConfigurationError(ParserError, CommonConfigurationError):
    """Raised when configuration is invalid or missing required settings."""


class ProviderAPIError(ParserError, RetryableError):
    """Raised when a third-party API provider returns an error."""


class DebugArtifactError(ParserError):
    """Raised when debug artifact generation or retrieval fails."""
