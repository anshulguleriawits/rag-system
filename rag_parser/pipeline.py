from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from haystack import Document

from rag_parser.logging_setup import get_logger
from rag_parser.routing.router import ParserRouter
from rag_common import timed_operation

logger = get_logger(__name__)


class ParsingPipeline:
    """Assembled parsing flow using the ParserRouter.

    Wraps the ParserRouter (itself a Haystack @component) and enriches
    output Documents with standard meta schema fields that downstream
    modules can rely on.
    """

    def __init__(self) -> None:
        self._router = ParserRouter()
        self._version = "1.0.0"

    @timed_operation("parse:pipeline")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
        force_parser: str | None = None,
    ) -> dict[str, list[Document] | list[tuple[str, str]]]:
        """Parse a list of source files through the full pipeline.

        Args:
            sources: List of file paths or URLs to parse.
            meta: Optional list of metadata dicts (one per source).
            force_parser: Override strategy selection for all files.

        Returns:
            dict with keys:
                - "documents": list of Haystack Documents
                - "errors": list of (file_path, error_message) tuples
        """
        logger.info(
            "Parsing pipeline run",
            num_sources=len(sources),
            force_parser=force_parser,
        )

        result = self._router.run(
            sources=sources,
            meta=meta,
            force_parser=force_parser,
        )

        docs = result.get("documents", [])
        errors = result.get("errors", [])

        docs = self._enrich_meta(docs, sources)

        logger.info(
            "Parsing pipeline completed",
            num_documents=len(docs),
            num_errors=len(errors),
        )

        return {
            "documents": docs,
            "errors": errors,
        }

    def _enrich_meta(
        self,
        docs: list[Document],
        sources: list[Path | str],
    ) -> list[Document]:
        """Ensure every Document has the standard meta schema fields."""
        for d in docs:
            if "document_id" not in d.meta or not d.meta.get("document_id"):
                d.meta["document_id"] = uuid.uuid4().hex[:16]
            if "parsing_duration_ms" not in d.meta:
                d.meta["parsing_duration_ms"] = 0
            if "warnings" not in d.meta:
                d.meta["warnings"] = []
            if "source_path" not in d.meta and "file_path" in d.meta:
                d.meta["source_path"] = d.meta["file_path"]
            if "mime_type" not in d.meta and "content_type" in d.meta:
                d.meta["mime_type"] = d.meta["content_type"]
        return docs
