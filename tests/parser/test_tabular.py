from __future__ import annotations

from pathlib import Path

import pytest
from haystack import Document

from components.parser.components.tabular import TabularParser


class TestTabularParser:
    @pytest.fixture
    def parser(self) -> TabularParser:
        return TabularParser()

    def test_csv(self, parser: TabularParser, sample_csv: Path) -> None:
        result = parser.run(sources=[sample_csv])
        docs = result["documents"]
        assert len(docs) >= 1
        meta = docs[0].meta
        assert meta["parser_used"] == "tabular:csv"
        assert meta["element_type"] == "table"

    def test_excel(self, parser: TabularParser, tmp_path: Path) -> None:
        import pandas as pd

        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        xlsx = tmp_path / "test.xlsx"
        df.to_excel(xlsx, index=False)

        result = parser.run(sources=[xlsx])
        docs = result["documents"]
        assert len(docs) >= 1
        meta = docs[0].meta
        assert meta["parser_used"] == "tabular:xlsx"
        assert meta["num_rows"] == 2
        assert meta["num_columns"] == 2
