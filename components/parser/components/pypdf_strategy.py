from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import Document, component

from common import timed_operation


@component
class PyPDFParser:
    """Parser for digital PDFs using Haystack's native PyPDFToDocument converter.

    Best for clean, text-layer PDFs without complex layout needs.
    """

    def __init__(self) -> None:
        self._converter = None
        self._version = "1.0.0"

    def _get_converter(self):
        if self._converter is None:
            from haystack.components.converters import PyPDFToDocument
            self._converter = PyPDFToDocument()
        return self._converter

    @component.output_types(documents=list[Document])
    @timed_operation("parse:pypdf")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        docs: list[Document] = []
        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}
            result = self._get_converter().run(sources=[path])
            for d in result.get("documents", []):
                d.meta.update(m)
                d.meta["parser_used"] = "pypdf"
                d.meta["parser_version"] = self._version
                d.meta["element_type"] = "paragraph"
                docs.append(d)

        return {"documents": docs}
