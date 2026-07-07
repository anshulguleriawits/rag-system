from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from haystack import Document

from common.schemas import META_KEY_SPEC
from common.testing import (
    log_context_reset,
    mock_http_provider,
    temp_env_file,
    valid_document,
    valid_meta,
    schema_required_keys,
)


class TestFixtures:
    def test_log_context_reset_exists(self) -> None:
        assert callable(log_context_reset)

    def test_temp_env_file_creates_file(self, temp_env_file: Path) -> None:
        assert temp_env_file.exists()
        assert temp_env_file.suffix == ".env"

    def test_valid_meta_has_all_required_keys(self, valid_meta: dict) -> None:
        required = [k for k, spec in META_KEY_SPEC.items() if spec.get("required")]
        for key in required:
            assert key in valid_meta, f"Missing required key: {key}"

    def test_valid_document_is_haystack_document(
        self, valid_document: Document
    ) -> None:
        assert isinstance(valid_document, Document)
        assert valid_document.content == "Test content"

    def test_valid_document_has_meta(self, valid_document: Document) -> None:
        assert valid_document.meta is not None
        assert valid_document.meta["document_id"] == "abc123def4567890"

    def test_schema_required_keys_list(self, schema_required_keys: list[str]) -> None:
        assert "document_id" in schema_required_keys
        assert "source_path" in schema_required_keys
        assert all(isinstance(k, str) for k in schema_required_keys)


class TestMockHttpProvider:
    def test_returns_magic_mock(self) -> None:
        mock = mock_http_provider()
        assert isinstance(mock, MagicMock)

    def test_default_status_code(self) -> None:
        mock = mock_http_provider()
        assert mock.status_code == 200

    def test_custom_status_code(self) -> None:
        mock = mock_http_provider(status_code=429)
        assert mock.status_code == 429

    def test_custom_response(self) -> None:
        mock = mock_http_provider(default_response={"result": "ok"})
        assert mock.json() == {"result": "ok"}

    def test_has_raise_for_status(self) -> None:
        mock = mock_http_provider()
        assert callable(mock.raise_for_status)

    def test_has_text(self) -> None:
        mock = mock_http_provider(default_response={"key": "val"})
        assert isinstance(mock.text, str)
