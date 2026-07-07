from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import Document, component

from rag_common import timed_operation


@component
class DoclingParser:
    """Layout-aware parser for PDF, DOCX, HTML using Docling via docling-haystack.

    Preserves tables, heading hierarchy, sections, and reading order.
    Uses ExportType.DOC_CHUNKS by default for structure-aware output.
    Lazily initializes the Docling converter to avoid heavy imports at module load.
    """

    def __init__(
        self,
        export_type: str = "doc_chunks",
    ) -> None:
        self._converter = None
        self._export_type = export_type
        self._version = "1.0.0"

    def _get_converter(self):
        if self._converter is None:
            from docling.chunking import HybridChunker
            from docling.document_converter import DocumentConverter
            from haystack_integrations.components.converters.docling import (
                DoclingConverter,
            )

            converter = DocumentConverter()
            chunker = HybridChunker()

            export_map = {
                "doc_chunks": "doc_chunks",
                "markdown": "markdown",
                "json": "json",
            }

            self._converter = DoclingConverter(
                converter=converter,
                export_type=export_map.get(self._export_type, "doc_chunks"),
                chunker=chunker,
            )
        return self._converter

    @component.output_types(documents=list[Document])
    @timed_operation("parse:docling")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        result = self._get_converter().run(sources=sources, meta=meta)
        for d in result.get("documents", []):
            d.meta["parser_used"] = "docling"
            d.meta["parser_version"] = self._version
            if "element_type" not in d.meta or not d.meta.get("element_type"):
                d.meta["element_type"] = "paragraph"
        return result
