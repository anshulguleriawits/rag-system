from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Literal

from haystack import Document, component

from rag_parser.config import config
from rag_parser.exceptions import (
    AllStrategiesFailedError,
    ParserNotFoundError,
)
from rag_parser.logging_setup import get_logger
from rag_parser.routing.scanned_detector import is_scanned_pdf
from rag_common import timed_operation

logger = get_logger(__name__)

StrategyName = Literal[
    "auto",
    "simple",
    "pypdf",
    "docling",
    "ocr_local",
    "ocr_cloud",
    "code",
    "tabular",
    "structured",
]

# Default strategy mapping by file extension family
EXTENSION_STRATEGY: dict[str, StrategyName] = {
    ".txt": "simple",
    ".md": "simple",
    ".html": "simple",
    ".htm": "simple",
    ".pdf": "auto",
    ".docx": "docling",
    ".doc": "docling",
    ".pptx": "docling",
    ".ppt": "docling",
    ".png": "ocr_local",
    ".jpg": "ocr_local",
    ".jpeg": "ocr_local",
    ".tiff": "ocr_local",
    ".tif": "ocr_local",
    ".bmp": "ocr_local",
    ".csv": "tabular",
    ".tsv": "tabular",
    ".xlsx": "tabular",
    ".xls": "tabular",
    ".parquet": "tabular",
    ".json": "structured",
    ".yaml": "structured",
    ".yml": "structured",
    ".xml": "structured",
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".tsx": "code",
    ".go": "code",
    ".java": "code",
    ".rs": "code",
    ".rb": "code",
    ".c": "code",
    ".cpp": "code",
    ".h": "code",
    ".hpp": "code",
}


@component
class ParserRouter:
    """Routes files to the appropriate parser strategy.

    Uses FileTypeRouter's MIME-based routing extended with:
    - Scanned-PDF detection (overrides to OCR if no text layer)
    - explicit caller override (force_parser)
    - fallback chain on failure
    """

    def __init__(self) -> None:
        self._strategies: dict[str, Any] = {}
        self._version = "1.0.0"

    def _get_strategy(self, name: str) -> Any:
        """Lazy-load and cache parser component by name."""
        if name not in self._strategies:
            self._strategies[name] = self._create_strategy(name)
        return self._strategies[name]

    def _create_strategy(self, name: str) -> Any:
        from rag_parser.components.code import CodeParser
        from rag_parser.components.docling_strategy import DoclingParser
        from rag_parser.components.ocr_cloud import CloudOCRParser
        from rag_parser.components.ocr_local import LocalOCRParser
        from rag_parser.components.pypdf_strategy import PyPDFParser
        from rag_parser.components.simple import SimpleParser
        from rag_parser.components.structured import StructuredParser
        from rag_parser.components.tabular import TabularParser

        factories = {
            "simple": SimpleParser,
            "pypdf": PyPDFParser,
            "docling": DoclingParser,
            "ocr_local": LocalOCRParser,
            "ocr_cloud": CloudOCRParser,
            "code": CodeParser,
            "tabular": TabularParser,
            "structured": StructuredParser,
        }
        factory = factories.get(name)
        if factory is None:
            raise ParserNotFoundError(f"Unknown parser strategy: {name}")
        return factory()

    def select_strategy(
        self,
        path: Path | str,
        force_parser: str | None = None,
    ) -> str:
        """Select the best strategy for a given file.

        Returns the strategy name string.
        """
        path = Path(path)

        # Explicit override takes priority
        if force_parser and force_parser != "auto":
            if force_parser in ("simple", "pypdf", "docling", "ocr_local", "ocr_cloud", "code", "tabular", "structured"):
                logger.info(
                    "Strategy explicitly overridden",
                    path=str(path),
                    strategy=force_parser,
                )
                return force_parser
            else:
                raise ParserNotFoundError(
                    f"Unknown parser strategy: {force_parser}. "
                    f"Available: simple, pypdf, docling, ocr_local, ocr_cloud, code, tabular, structured"
                )

        ext = path.suffix.lower()

        # Auto-detect: scanned PDF detection for .pdf files
        if ext == ".pdf":
            if is_scanned_pdf(path):
                logger.info(
                    "Auto-selected ocr_cloud for scanned PDF",
                    path=str(path),
                    reason="scanned_detection",
                )
                return "ocr_cloud"
            else:
                logger.info(
                    "Auto-selected docling for digital PDF",
                    path=str(path),
                    reason="digital_detection",
                )
                return "docling"

        strategy = EXTENSION_STRATEGY.get(ext, "simple")
        logger.info(
            "Auto-selected strategy by extension",
            path=str(path),
            extension=ext,
            strategy=strategy,
        )
        return strategy

    @component.output_types(documents=list[Document], errors=list[tuple[str, str]])
    @timed_operation("parse:router")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
        force_parser: str | None = None,
    ) -> dict[str, list[Document] | list[tuple[str, str]]]:
        """Parse a list of source files, auto-routing each to its best strategy.

        Each file gets its own strategy selection. Failed files go through
        the fallback chain. Documents accumulate across all files.
        """
        all_docs: list[Document] = []
        errors: list[tuple[str, str]] = []

        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}

            try:
                strategy_name = self.select_strategy(path, force_parser)
                docs = self._run_with_fallback(
                    path, strategy_name, m
                )
                all_docs.extend(docs)
            except AllStrategiesFailedError as e:
                errors.append((str(path), str(e)))
                logger.error(
                    "All strategies failed for file",
                    path=str(path),
                    error=str(e),
                )

        return {"documents": all_docs, "errors": errors}

    def _run_with_fallback(
        self,
        path: Path,
        strategy_name: str,
        base_meta: dict[str, Any],
    ) -> list[Document]:
        """Try the selected strategy, then fallback chain on failure."""

        strategies_to_try = [strategy_name]
        for fb in config.fallback_strategies:
            fb = fb.strip()
            if fb and fb != strategy_name and fb in ("simple", "pypdf", "docling", "ocr_local", "ocr_cloud", "code", "tabular", "structured"):
                strategies_to_try.append(fb)

        last_error: Exception | None = None
        for sname in strategies_to_try:
            try:
                component = self._get_strategy(sname)
                m = dict(base_meta)
                start = time.monotonic()

                # Run the component
                result = component.run(sources=[path], meta=[m])

                docs = result.get("documents", [])
                for d in docs:
                    if "parser_used" not in d.meta or not d.meta.get("parser_used"):
                        d.meta["parser_used"] = sname
                    if "parsing_duration_ms" not in d.meta:
                        d.meta["parsing_duration_ms"] = int(
                            (time.monotonic() - start) * 1000
                        )

                if docs:
                    logger.info(
                        "Parse succeeded",
                        path=str(path),
                        strategy=sname,
                        num_docs=len(docs),
                    )
                    return docs

                last_error = ValueError(
                    f"{sname} returned zero documents"
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    "Strategy failed, trying fallback",
                    path=str(path),
                    strategy=sname,
                    error=str(e),
                )
                continue

        raise AllStrategiesFailedError(
            f"File {path}: all {len(strategies_to_try)} strategies failed. "
            f"Tried: {strategies_to_try}. Last error: {last_error}"
        )
