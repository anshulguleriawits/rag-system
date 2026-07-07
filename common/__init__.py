"""rag-common: shared foundation package for the RAG platform.

Cross-cutting infrastructure shared by all RAG modules — logging, config,
exceptions, schemas, observability, and testing utilities.

Explicitly contains no RAG-specific logic (no parsing, chunking, embedding,
retrieval). See `MIGRATION.md` for guidance on retrofitting existing modules.
"""

from common.logging import get_logger, log_context
from common.config import BaseServiceSettings, fail_fast_validation
from common.exceptions import (
    RagBaseError,
    ConfigurationError,
    RetryableError,
    TerminalError,
    ValidationError,
)
from common.schemas import Document, validate_meta
from common.observability import timed_operation

__all__ = [
    "get_logger",
    "log_context",
    "BaseServiceSettings",
    "fail_fast_validation",
    "RagBaseError",
    "ConfigurationError",
    "RetryableError",
    "TerminalError",
    "ValidationError",
    "Document",
    "validate_meta",
    "timed_operation",
]
