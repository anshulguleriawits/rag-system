from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from haystack import Document

from rag_parser.components.structured import StructuredParser


class TestStructuredParser:
    @pytest.fixture
    def parser(self) -> StructuredParser:
        return StructuredParser()

    def test_json(self, parser: StructuredParser, sample_json: Path) -> None:
        result = parser.run(sources=[sample_json])
        docs = result["documents"]
        assert len(docs) >= 1
        assert docs[0].meta["parser_used"] == "structured:json"
        assert "test-config" in docs[0].content

    def test_yaml(self, parser: StructuredParser, tmp_path: Path) -> None:
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key1: value1\nkey2: 42\nnested:\n  inner: hello\n")
        result = parser.run(sources=[yaml_file])
        docs = result["documents"]
        assert len(docs) >= 1
        assert docs[0].meta["parser_used"] == "structured:yaml"
        assert "key1" in docs[0].content

    def test_xml(self, parser: StructuredParser, tmp_path: Path) -> None:
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(
            '<root><item id="1"><name>Alice</name></item></root>'
        )
        result = parser.run(sources=[xml_file])
        docs = result["documents"]
        assert len(docs) >= 1
        assert docs[0].meta["parser_used"] == "structured:xml"
