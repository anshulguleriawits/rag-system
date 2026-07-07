from __future__ import annotations

import pytest

from rag_common.exceptions import (
    RagBaseError,
    ConfigurationError,
    RetryableError,
    TerminalError,
    ValidationError,
)


class TestRagBaseError:
    def test_default_message(self) -> None:
        err = RagBaseError()
        assert err.message == ""

    def test_message_and_context(self) -> None:
        err = RagBaseError("something broke", context={"file": "test.pdf"})
        assert err.message == "something broke"
        assert err.context == {"file": "test.pdf"}
        assert err.retryable is False

    def test_retryable_default(self) -> None:
        err = RagBaseError()
        assert err.retryable is False

    def test_retryable_override(self) -> None:
        err = RagBaseError(retryable=True)
        assert err.retryable is True

    def test_string_representation(self) -> None:
        err = RagBaseError("test error")
        assert str(err) == "test error"

    def test_is_exception_subclass(self) -> None:
        err = RagBaseError("test")
        assert isinstance(err, Exception)


class TestConfigurationError:
    def test_inherits_from_rag_base(self) -> None:
        err = ConfigurationError("bad config")
        assert isinstance(err, RagBaseError)
        assert isinstance(err, Exception)

    def test_non_retryable(self) -> None:
        err = ConfigurationError("bad config")
        assert err.retryable is False

    def test_message(self) -> None:
        err = ConfigurationError("MISSING_API_KEY is not set")
        assert "MISSING_API_KEY" in err.message


class TestRetryableError:
    def test_inherits_from_rag_base(self) -> None:
        err = RetryableError("timeout")
        assert isinstance(err, RagBaseError)

    def test_retryable_flag(self) -> None:
        err = RetryableError("timeout")
        assert err.retryable is True

    def test_retries_remaining_default(self) -> None:
        err = RetryableError("timeout")
        assert err.retries_remaining == 0

    def test_retries_remaining_custom(self) -> None:
        err = RetryableError("timeout", retries_remaining=3)
        assert err.retries_remaining == 3


class TestTerminalError:
    def test_inherits_from_rag_base(self) -> None:
        err = TerminalError("exhausted")
        assert isinstance(err, RagBaseError)

    def test_non_retryable(self) -> None:
        err = TerminalError("exhausted")
        assert err.retryable is False


class TestValidationError:
    def test_inherits_from_rag_base(self) -> None:
        err = ValidationError("bad input")
        assert isinstance(err, RagBaseError)

    def test_non_retryable(self) -> None:
        err = ValidationError("bad input")
        assert err.retryable is False

    def test_context(self) -> None:
        err = ValidationError("schema mismatch", context={"field": "document_id"})
        assert err.context["field"] == "document_id"


class TestInheritance:
    def test_all_subclasses_are_rag_base_errors(self) -> None:
        errors = [ConfigurationError, RetryableError, TerminalError, ValidationError]
        for exc_type in errors:
            assert issubclass(exc_type, RagBaseError)
            assert issubclass(exc_type, Exception)

    def test_exception_hierarchy_catch_by_base(self) -> None:
        errors = [
            ConfigurationError("a"),
            RetryableError("b"),
            TerminalError("c"),
            ValidationError("d"),
        ]
        for err in errors:
            assert isinstance(err, RagBaseError)
            assert isinstance(err, Exception)
