from __future__ import annotations

from pathlib import Path

import pytest
from haystack import Document

from rag_parser.components.simple import SimpleParser


class TestSimpleParser:
    @pytest.fixture
    def parser(self) -> SimpleParser:
        return SimpleParser()

    def test_txt(self, parser: SimpleParser, sample_txt: Path) -> None:
        result = parser.run(sources=[sample_txt])
        docs = result["documents"]
        assert len(docs) == 1
        assert "Hello, world!" in docs[0].content
        assert docs[0].meta["parser_used"].startswith("simple:")

    def test_md(self, parser: SimpleParser, sample_md: Path) -> None:
        result = parser.run(sources=[sample_md])
        docs = result["documents"]
        assert len(docs) >= 1
        assert docs[0].meta["parser_used"].startswith("simple:")

    def test_html(self, parser: SimpleParser, sample_html: Path) -> None:
        result = parser.run(sources=[sample_html])
        docs = result["documents"]
        assert len(docs) >= 1
        assert "Test HTML" in docs[0].content

    def test_meta_passthrough(
        self, parser: SimpleParser, sample_txt: Path
    ) -> None:
        meta = [{"test_key": "test_value", "document_id": "custom-id"}]
        result = parser.run(sources=[sample_txt], meta=meta)
        docs = result["documents"]
        assert docs[0].meta["test_key"] == "test_value"
