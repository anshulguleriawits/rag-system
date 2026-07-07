from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from common.schemas import META_KEY_SPEC
from haystack import Document


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def log_context_reset() -> Generator[None, None, None]:
    """Fixture that resets log context variables after each test.

    Use in any test that calls ``log_context(...)`` to avoid cross-test
    leakage of correlation IDs.
    """
    from common.logging import _log_context_var

    token = _log_context_var.set({})
    try:
        yield
    finally:
        _log_context_var.reset(token)


@pytest.fixture
def temp_env_file() -> Generator[Path, None, None]:
    """Fixture that creates a temporary ``.env`` file for config tests.

    Yields the path to a temporary ``.env`` file. The file is cleaned up
    after the test. Use with ``monkeypatch`` to set ``ENV_FILE`` or similar.
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".env", delete=False, prefix="test_"
    ) as f:
        env_path = Path(f.name)
    try:
        yield env_path
    finally:
        if env_path.exists():
            os.unlink(env_path)


@pytest.fixture
def valid_meta() -> dict[str, Any]:
    """Fixture returning a canonical valid meta dict for testing."""
    return {
        "document_id": "abc123def4567890",
        "source_path": "/tmp/test.pdf",
        "mime_type": "application/pdf",
        "parser_used": "docling",
        "parser_version": "1.0.0",
        "page_number": None,
        "section_path": [],
        "element_type": "paragraph",
        "confidence": 0.95,
        "parsing_duration_ms": 150,
        "warnings": [],
    }


@pytest.fixture
def valid_document(valid_meta: dict[str, Any]) -> Document:
    """Fixture returning a Haystack ``Document`` with valid meta."""
    return Document(content="Test content", meta=valid_meta)


@pytest.fixture
def schema_required_keys() -> list[str]:
    """Fixture returning the list of meta keys marked ``required`` in the schema."""
    return [k for k, spec in META_KEY_SPEC.items() if spec.get("required")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def mock_http_provider(
    base_url: str = "https://api.example.com",
    default_response: dict[str, Any] | None = None,
    status_code: int = 200,
) -> MagicMock:
    """Create a mock for a third-party HTTP provider.

    Returns a ``MagicMock`` configured as a callable that returns
    ``httpx.Response``-like objects. Use this in tests for any module
    (rag-parser, rag-embedder, rag-retriever) that calls external APIs.

    Args:
        base_url: The base URL the mock pretends to serve.
        default_response: JSON body the mock returns by default.
        status_code: HTTP status code the mock returns by default.

    Usage::

        mock_provider = mock_http_provider(
            base_url="https://api.mistral.ai",
            default_response={"status": "ok"},
        )
        with patch("components.parser.components.ocr_cloud.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.post = mock_provider
            ...
    """
    import httpx

    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = default_response or {}
    mock.text = str(default_response or {})
    mock.raise_for_status = MagicMock()
    return mock
