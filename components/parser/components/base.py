from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from haystack import Document, component


@component
class BaseParserComponent(ABC):
    """Abstract base for all parser strategy components.

    Every parser component wraps a Haystack @component decorated class
    with a consistent run(sources, meta) -> {"documents": list[Document]} interface.
    """

    def __init__(self) -> None:
        self._version = self._detect_version()

    def _detect_version(self) -> str:
        return "0.1.0"

    @abstractmethod
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        ...

    def to_dict(self) -> dict[str, Any]:
        return {"type": f"{__name__}.{type(self).__name__}", "init_parameters": {}}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaseParserComponent:
        return cls()
