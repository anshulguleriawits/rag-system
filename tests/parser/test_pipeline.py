from __future__ import annotations

from pathlib import Path

import pytest

from components.parser.pipeline import ParsingPipeline


class TestParsingPipeline:
    @pytest.fixture
    def pipeline(self) -> ParsingPipeline:
        return ParsingPipeline()

    def test_run_txt(self, pipeline: ParsingPipeline, sample_txt: Path) -> None:
        result = pipeline.run(sources=[sample_txt])
        docs = result.get("documents", [])
        assert len(docs) >= 1
        d = docs[0]
        # Verify meta schema compliance
        meta = d.meta
        assert "document_id" in meta
        assert "source_path" in meta
        assert "parser_used" in meta
        assert meta["parser_used"].startswith("simple:")
        assert "element_type" in meta
        assert "parsing_duration_ms" in meta

    def test_run_csv(self, pipeline: ParsingPipeline, sample_csv: Path) -> None:
        result = pipeline.run(sources=[sample_csv])
        docs = result.get("documents", [])
        assert len(docs) >= 1
        assert docs[0].meta["element_type"] == "table"

    def test_run_json(self, pipeline: ParsingPipeline, sample_json: Path) -> None:
        result = pipeline.run(sources=[sample_json])
        docs = result.get("documents", [])
        assert len(docs) >= 1
        assert docs[0].meta["element_type"] == "structured"
        assert "structured" in docs[0].meta["parser_used"]

    def test_run_py(self, pipeline: ParsingPipeline, sample_py: Path) -> None:
        result = pipeline.run(sources=[sample_py])
        docs = result.get("documents", [])
        assert len(docs) >= 1

    def test_run_pdf(
        self, pipeline: ParsingPipeline, sample_digital_pdf: Path
    ) -> None:
        result = pipeline.run(sources=[sample_digital_pdf])
        docs = result.get("documents", [])
        errors = result.get("errors", [])
        # PDFs require docling which needs the model download
        # This may produce 0 docs if deps aren't available
        # But should not crash
        assert isinstance(docs, list)
        assert isinstance(errors, list)

    def test_force_parser(
        self, pipeline: ParsingPipeline, sample_txt: Path
    ) -> None:
        result = pipeline.run(
            sources=[sample_txt], force_parser="code"
        )
        docs = result.get("documents", [])
        assert len(docs) >= 1
        for d in docs:
            assert "code" in d.meta["parser_used"]
