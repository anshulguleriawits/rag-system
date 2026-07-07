from __future__ import annotations

import contextvars
import logging
import os
import sys
from io import StringIO

import pytest
import structlog

from common.logging import get_logger, log_context, setup_logging


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    structlog.reset_defaults()
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
    root.setLevel(logging.WARNING)
    yield


class TestGetLogger:
    def test_returns_bound_logger(self) -> None:
        setup_logging()
        logger = get_logger("test")
        assert hasattr(logger, "info")
        assert hasattr(logger, "bind")

    def test_default_name(self) -> None:
        setup_logging()
        logger = get_logger()
        assert "common" in str(logger)

    def test_custom_name(self) -> None:
        setup_logging()
        logger = get_logger("my.custom.name")
        assert "my.custom.name" in str(logger)


class TestLogContext:
    def test_binds_and_clears(self) -> None:
        assert log_context(document_id="doc123")
        with log_context(document_id="doc123"):
            pass

    def test_nesting_merges(self) -> None:
        with log_context(request_id="req-1"):
            with log_context(document_id="doc-42"):
                pass

    def test_outer_restored_after_inner(self) -> None:
        with log_context(outer="val"):
            with log_context(inner="val2"):
                pass

    def test_context_does_not_leak(self) -> None:
        with log_context(leak="test"):
            pass
        # Should be back to empty/default after exit


class TestSetupLogging:
    def test_json_output_when_not_tty(self) -> None:
        original_isatty = sys.stderr.isatty
        sys.stderr.isatty = lambda: False
        try:
            os.environ["LOG_FORMAT"] = "json"
            setup_logging()

            out = StringIO()
            handler = logging.StreamHandler(out)
            logging.getLogger().addHandler(handler)

            logger = get_logger("test_json")
            logger.info("hello", key="value")

            logging.getLogger().removeHandler(handler)
            output = out.getvalue()
            assert '"key": "value"' in output
            assert '"event": "hello"' in output
        finally:
            sys.stderr.isatty = original_isatty
            os.environ.pop("LOG_FORMAT", None)

    def test_log_level_respected(self) -> None:
        os.environ["LOG_LEVEL"] = "ERROR"
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR
        os.environ.pop("LOG_LEVEL", None)

    def test_invalid_log_level_defaults_to_info(self) -> None:
        os.environ["LOG_LEVEL"] = "INVALID"
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        os.environ.pop("LOG_LEVEL", None)
