from __future__ import annotations

from pathlib import Path
from typing import Any

from haystack import Document, component

from rag_common import timed_operation


@component
class CodeParser:
    """Parser for source code files using tree-sitter.

    Splits code by function/class/top-level boundaries, preserving
    docstrings, imports, and language metadata. Falls back to line-based
    splitting when tree-sitter grammar is unavailable.

    Currently supports Python fully. Other languages get basic line-splitting.
    """

    LANGUAGE_MAP: dict[str, str] = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".go": "go",
        ".java": "java",
        ".rs": "rust",
        ".rb": "ruby",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }

    def __init__(self) -> None:
        self._version = "1.0.0"
        self._parsers: dict[str, Any] = {}
        self._init_parsers()

    def _init_parsers(self) -> None:
        try:
            import tree_sitter_python as tspython

            from tree_sitter import Language, Parser

            py_lang = Language(tspython.language())
            py_parser = Parser(py_lang)
            self._parsers["python"] = py_parser
        except Exception:
            pass

    @component.output_types(documents=list[Document])
    @timed_operation("parse:code")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        docs: list[Document] = []
        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}
            content = path.read_text(encoding="utf-8", errors="replace")
            ext = path.suffix.lower()
            lang = self.LANGUAGE_MAP.get(ext, "unknown")

            blocks = self._parse_blocks(content, lang)
            for j, (block_type, block_content) in enumerate(blocks):
                doc_meta = dict(m)
                doc_meta["parser_used"] = f"code:{lang}"
                doc_meta["parser_version"] = self._version
                doc_meta["element_type"] = block_type
                doc_meta["language"] = lang
                doc_meta["source_path"] = str(path)
                doc_meta["block_index"] = j
                docs.append(
                    Document(content=block_content, meta=doc_meta)
                )

            if not blocks:
                doc_meta = dict(m)
                doc_meta["parser_used"] = f"code:{lang}"
                doc_meta["parser_version"] = self._version
                doc_meta["element_type"] = "code_block"
                doc_meta["language"] = lang
                doc_meta["source_path"] = str(path)
                docs.append(Document(content=content, meta=doc_meta))

        return {"documents": docs}

    def _parse_blocks(
        self, content: str, language: str
    ) -> list[tuple[str, str]]:
        if language == "python" and "python" in self._parsers:
            return self._parse_python(content)
        return self._fallback_split(content)

    def _parse_python(self, content: str) -> list[tuple[str, str]]:
        parser = self._parsers["python"]
        tree = parser.parse(content.encode("utf-8"))
        root = tree.root_node
        blocks: list[tuple[str, str]] = []

        for child in root.children:
            block_type = child.type
            start_line = child.start_point[0]
            end_line = child.end_point[0]
            text = "\n".join(
                content.splitlines()[start_line : end_line + 1]
            )

            if block_type == "class_definition":
                blocks.append(("class_definition", text))
            elif block_type == "function_definition":
                blocks.append(("function_definition", text))
            elif block_type == "decorated_definition":
                blocks.append(("decorated_definition", text))
            elif block_type == "import_statement":
                blocks.append(("import", text))
            elif block_type == "import_from_statement":
                blocks.append(("import", text))
            else:
                text_stripped = text.strip()
                if text_stripped and len(text_stripped) > 20:
                    blocks.append(("code_block", text))

        return blocks

    def _fallback_split(
        self, content: str
    ) -> list[tuple[str, str]]:
        lines = content.splitlines()
        blocks: list[tuple[str, str]] = []
        current: list[str] = []
        current_type = "code_block"

        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith("def ")
                or stripped.startswith("class ")
                or stripped.startswith("function ")
            ):
                if current:
                    blocks.append((current_type, "\n".join(current)))
                current = [line]
                current_type = (
                    "function_definition"
                    if stripped.startswith("def ") or stripped.startswith("function ")
                    else "class_definition"
                )
            elif (
                stripped.startswith("import ")
                or stripped.startswith("from ")
            ):
                if current and current_type not in (
                    "import",
                    "import_statement",
                ):
                    blocks.append((current_type, "\n".join(current)))
                    current = []
                current_type = "import"
                current.append(line)
            else:
                current.append(line)

        if current:
            blocks.append((current_type, "\n".join(current)))

        return blocks
