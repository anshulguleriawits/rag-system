from __future__ import annotations

from pathlib import Path

import pytest
from haystack import Document

from components.parser.components.code import CodeParser


class TestCodeParser:
    @pytest.fixture
    def parser(self) -> CodeParser:
        return CodeParser()

    def test_python(self, parser: CodeParser, sample_py: Path) -> None:
        result = parser.run(sources=[sample_py])
        docs = result["documents"]
        assert len(docs) >= 1
        parsers_used = {d.meta["parser_used"] for d in docs}
        assert any("code:python" in p for p in parsers_used)

        types_found = {d.meta["element_type"] for d in docs}
        assert "function_definition" in types_found or "class_definition" in types_found

    def test_unknown_extension(
        self, parser: CodeParser, tmp_path: Path
    ) -> None:
        f = tmp_path / "test.unknown"
        f.write_text("some random text\nmore text\n")
        result = parser.run(sources=[f])
        docs = result["documents"]
        assert len(docs) >= 1
