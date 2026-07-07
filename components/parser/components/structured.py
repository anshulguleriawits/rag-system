from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from haystack import Document, component

from common import timed_operation


@component
class StructuredParser:
    """Parser for structured data files (.json, .yaml, .xml).

    For JSON/YAML/XML uses custom parsing that preserves key paths.
    """

    def __init__(self) -> None:
        self._version = "1.0.0"

    @component.output_types(documents=list[Document])
    @timed_operation("parse:structured")
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

            if ext == ".json":
                doc = self._parse_json(path, m)
                docs.append(doc)
            elif ext in (".yaml", ".yml"):
                doc = self._parse_yaml(path, m)
                docs.append(doc)
            elif ext == ".xml":
                doc = self._parse_xml(path, m)
                docs.append(doc)

        return {"documents": docs}

    def _parse_json(
        self, path: Path, meta: dict[str, Any]
    ) -> Document:
        with open(path) as f:
            data = json.load(f)

        lines = self._flatten("", data)
        content = "# JSON Document: {}\n\n{}".format(
            path.name, "\n".join(lines)
        )
        doc_meta = dict(meta)
        doc_meta["parser_used"] = "structured:json"
        doc_meta["parser_version"] = self._version
        doc_meta["element_type"] = "structured"
        doc_meta["source_path"] = str(path)
        return Document(content=content, meta=doc_meta)

    def _parse_yaml(
        self, path: Path, meta: dict[str, Any]
    ) -> Document:
        with open(path) as f:
            data = yaml.safe_load(f)

        lines = self._flatten("", data)
        content = "# YAML Document: {}\n\n{}".format(
            path.name, "\n".join(lines)
        )
        doc_meta = dict(meta)
        doc_meta["parser_used"] = "structured:yaml"
        doc_meta["parser_version"] = self._version
        doc_meta["element_type"] = "structured"
        doc_meta["source_path"] = str(path)
        return Document(content=content, meta=doc_meta)

    def _parse_xml(
        self, path: Path, meta: dict[str, Any]
    ) -> Document:
        import xml.etree.ElementTree as ET

        tree = ET.parse(path)
        root = tree.getroot()

        lines = self._flatten_xml(root)
        content = "# XML Document: {}\n\n{}".format(
            path.name, "\n".join(lines)
        )
        doc_meta = dict(meta)
        doc_meta["parser_used"] = "structured:xml"
        doc_meta["parser_version"] = self._version
        doc_meta["element_type"] = "structured"
        doc_meta["source_path"] = str(path)
        return Document(content=content, meta=doc_meta)

    @staticmethod
    def _flatten(
        prefix: str, data: Any, depth: int = 0
    ) -> list[str]:
        lines: list[str] = []
        indent = "  " * depth
        if isinstance(data, dict):
            for k, v in data.items():
                key_path = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    lines.append(f"{indent}- **{key_path}:**")
                    lines.extend(
                        StructuredParser._flatten(key_path, v, depth + 1)
                    )
                else:
                    lines.append(
                        f"{indent}- `{key_path}`: {repr(v)}"
                    )
        elif isinstance(data, list):
            for i, item in enumerate(data):
                item_path = f"{prefix}[{i}]"
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}- **{item_path}:**")
                    lines.extend(
                        StructuredParser._flatten(
                            item_path, item, depth + 1
                        )
                    )
                else:
                    lines.append(
                        f"{indent}- `{item_path}`: {repr(item)}"
                    )
        else:
            lines.append(f"{indent}- `{prefix}`: {repr(data)}")
        return lines

    @staticmethod
    def _flatten_xml(
        element: Any, prefix: str = "", depth: int = 0
    ) -> list[str]:
        lines: list[str] = []
        indent = "  " * depth
        tag = element.tag
        attribs = element.attrib
        text = (element.text or "").strip()
        key_path = f"{prefix}/{tag}" if prefix else f"/{tag}"

        parts = [f"{indent}- **{key_path}**"]
        if attribs:
            parts.append(
                f" [{', '.join(f'{k}={v!r}' for k, v in attribs.items())}]"
            )
        if text:
            parts.append(f": {text}")
        lines.append("".join(parts))

        for child in element:
            lines.extend(
                StructuredParser._flatten_xml(child, key_path, depth + 1)
            )

        return lines
