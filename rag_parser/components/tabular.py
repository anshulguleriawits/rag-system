from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import Document, component
from haystack.components.converters import CSVToDocument

from rag_common import timed_operation


@component
class TabularParser:
    """Parser for tabular data files (.csv, .tsv, .xlsx, .parquet).

    For CSV/TSV uses Haystack's native CSVToDocument.
    For Excel/Parquet uses pandas to extract schema + representative rows + basic stats.
    """

    def __init__(self) -> None:
        self._csv = CSVToDocument()
        self._version = "1.0.0"

    @component.output_types(documents=list[Document])
    @timed_operation("parse:tabular")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        docs: list[Document] = []
        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}
            ext = path.suffix.lower()

            if ext in (".csv", ".tsv"):
                result = self._csv.run(sources=[path])
                for d in result.get("documents", []):
                    d.meta.update(m)
                    d.meta["parser_used"] = "tabular:csv"
                    d.meta["parser_version"] = self._version
                    d.meta["element_type"] = "table"
                    docs.append(d)
            elif ext in (".xlsx", ".xls"):
                doc = self._parse_excel(path, m)
                docs.append(doc)
            elif ext == ".parquet":
                doc = self._parse_parquet(path, m)
                docs.append(doc)

        return {"documents": docs}

    def _parse_excel(
        self, path: Path, meta: dict[str, Any]
    ) -> Document:
        import pandas as pd

        df = pd.read_excel(path)
        content = self._tabular_summary(df, path.name)
        doc_meta = dict(meta)
        doc_meta["parser_used"] = "tabular:xlsx"
        doc_meta["parser_version"] = self._version
        doc_meta["element_type"] = "table"
        doc_meta["source_path"] = str(path)
        doc_meta["num_rows"] = len(df)
        doc_meta["num_columns"] = len(df.columns)
        doc_meta["columns"] = list(df.columns)
        return Document(content=content, meta=doc_meta)

    def _parse_parquet(
        self, path: Path, meta: dict[str, Any]
    ) -> Document:
        import pandas as pd

        df = pd.read_parquet(path)
        content = self._tabular_summary(df, path.name)
        doc_meta = dict(meta)
        doc_meta["parser_used"] = "tabular:parquet"
        doc_meta["parser_version"] = self._version
        doc_meta["element_type"] = "table"
        doc_meta["source_path"] = str(path)
        doc_meta["num_rows"] = len(df)
        doc_meta["num_columns"] = len(df.columns)
        doc_meta["columns"] = list(df.columns)
        return Document(content=content, meta=doc_meta)

    @staticmethod
    def _tabular_summary(df: Any, name: str) -> str:
        import io

        buf = io.StringIO()
        buf.write(f"# Table: {name}\n\n")
        buf.write(f"**Rows:** {len(df)}, **Columns:** {len(df.columns)}\n\n")
        buf.write("## Schema\n\n")
        buf.write("| Column | Type | Non-Null Count |\n")
        buf.write("|---|---|---|\n")
        for col in df.columns:
            buf.write(f"| {col} | {df[col].dtype} | {df[col].count()} |\n")

        buf.write("\n## Sample Rows (first 5)\n\n")
        buf.write(df.head(5).to_markdown(index=False))
        buf.write("\n\n## Basic Stats\n\n")
        numeric = df.select_dtypes(include="number")
        if not numeric.empty:
            buf.write(numeric.describe().to_markdown())
        return buf.getvalue()
