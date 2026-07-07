from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import Document, component

from common import timed_operation


@component
class SimpleParser:
    """Parser for plain text, markdown, and HTML files using Haystack native converters.

    Routes .txt -> TextFileToDocument, .md -> MarkdownToDocument, .html -> HTMLToDocument.
    Converters are lazy-loaded on first use to avoid optional dependency issues at import time.
    """

    def __init__(self) -> None:
        self._txt = None
        self._md = None
        self._html = None
        self._version = "1.0.0"

    def _get_txt(self):
        if self._txt is None:
            from haystack.components.converters import TextFileToDocument
            self._txt = TextFileToDocument()
        return self._txt

    def _get_md(self):
        if self._md is None:
            from haystack.components.converters import MarkdownToDocument
            self._md = MarkdownToDocument()
        return self._md

    def _get_html(self):
        if self._html is None:
            from haystack.components.converters import HTMLToDocument
            self._html = HTMLToDocument()
        return self._html

    @component.output_types(documents=list[Document])
    @timed_operation("parse:simple")
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

            if ext == ".md":
                result = self._get_md().run(sources=[path])
            elif ext == ".html":
                result = self._get_html().run(sources=[path])
            else:
                result = self._get_txt().run(sources=[path])

            for d in result.get("documents", []):
                d.meta.update(m)
                d.meta["parser_used"] = f"simple:{ext}"
                d.meta["parser_version"] = self._version
                d.meta["element_type"] = "paragraph"
                docs.append(d)

        return {"documents": docs}
