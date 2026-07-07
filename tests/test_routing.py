from __future__ import annotations

from pathlib import Path

import pytest

from rag_parser.routing.router import ParserRouter


class TestParserRouter:
    @pytest.fixture
    def router(self) -> ParserRouter:
        return ParserRouter()

    def test_select_txt(self, router: ParserRouter, sample_txt: Path) -> None:
        strategy = router.select_strategy(sample_txt)
        assert strategy == "simple"

    def test_select_csv(self, router: ParserRouter, sample_csv: Path) -> None:
        strategy = router.select_strategy(sample_csv)
        assert strategy == "tabular"

    def test_select_json(self, router: ParserRouter, sample_json: Path) -> None:
        strategy = router.select_strategy(sample_json)
        assert strategy == "structured"

    def test_select_py(self, router: ParserRouter, sample_py: Path) -> None:
        strategy = router.select_strategy(sample_py)
        assert strategy == "code"

    def test_select_pdf_digital(
        self, router: ParserRouter, sample_digital_pdf: Path
    ) -> None:
        strategy = router.select_strategy(sample_digital_pdf)
        # Digital PDF with text should route to docling
        assert strategy == "docling"

    def test_override_strategy(
        self, router: ParserRouter, sample_txt: Path
    ) -> None:
        strategy = router.select_strategy(
            sample_txt, force_parser="pypdf"
        )
        assert strategy == "pypdf"

    def test_override_unknown(
        self, router: ParserRouter, sample_txt: Path
    ) -> None:
        from rag_parser.exceptions import ParserNotFoundError

        with pytest.raises(ParserNotFoundError):
            router.select_strategy(sample_txt, force_parser="nonexistent")

    def test_run_single_file(
        self, router: ParserRouter, sample_txt: Path
    ) -> None:
        result = router.run(sources=[sample_txt])
        docs = result.get("documents", [])
        assert len(docs) >= 1
        assert docs[0].meta["parser_used"].startswith("simple")

    def test_run_pdf(
        self, router: ParserRouter, sample_digital_pdf: Path
    ) -> None:
        result = router.run(sources=[sample_digital_pdf])
        docs = result.get("documents", [])
        errors = result.get("errors", [])
        # Should either produce documents or fail gracefully
        assert len(errors) == 0 or len(docs) > 0

    def test_run_force_parser(
        self, router: ParserRouter, sample_txt: Path
    ) -> None:
        result = router.run(
            sources=[sample_txt], force_parser="pypdf"
        )
        docs = result.get("documents", [])
        # pypdf on a .txt file may produce empty docs or fail
        # The key is it doesn't crash
        assert "documents" in result
