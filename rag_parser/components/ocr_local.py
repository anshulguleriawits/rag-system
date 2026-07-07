from __future__ import annotations

import io
import time
import uuid
from pathlib import Path
from typing import Any

from haystack import Document, component
from PIL import Image

from rag_parser.config import config
from rag_common import timed_operation


@component
class LocalOCRParser:
    """Parser for scanned PDFs/images using local OCR engine (Tesseract).

    Rasterizes PDF pages to images via pdf2image, then runs OCR via pytesseract.
    Provides per-page confidence scores and supports debug artifact generation.
    """

    def __init__(self) -> None:
        self._version = "1.0.0"
        self._check_deps()

    def _check_deps(self) -> None:
        try:
            import pytesseract
        except ImportError:
            raise ImportError(
                "pytesseract is required for local OCR. "
                "Install with: pip install pytesseract"
            )
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image is required for local OCR. "
                "Install with: pip install pdf2image"
            )

    @component.output_types(documents=list[Document])
    @timed_operation("parse:ocr_local")
    def run(
        self,
        sources: list[Path | str],
        meta: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[Document]]:
        import pytesseract
        from pdf2image import convert_from_path

        docs: list[Document] = []
        for i, src in enumerate(sources):
            path = Path(src)
            m = meta[i] if meta and i < len(meta) else {}

            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
                image = Image.open(path)
                page_docs = self._ocr_image(
                    image, path, 0, m
                )
                docs.extend(page_docs)
            else:
                images = convert_from_path(str(path), dpi=300)
                for page_num, image in enumerate(images):
                    page_docs = self._ocr_image(
                        image, path, page_num, m
                    )
                    docs.extend(page_docs)

        return {"documents": docs}

    def _ocr_image(
        self,
        image: Image.Image,
        source_path: Path,
        page_num: int,
        base_meta: dict[str, Any],
    ) -> list[Document]:
        import pytesseract

        ocr_data = pytesseract.image_to_data(
            image,
            lang=config.ocr_local_language,
            output_type=pytesseract.Output.DICT,
        )

        text_parts: list[str] = []
        confidences: list[float] = []
        for j, txt in enumerate(ocr_data.get("text", [])):
            txt_stripped = (txt or "").strip()
            if txt_stripped:
                text_parts.append(txt_stripped)
                conf_str = ocr_data.get("conf", [])[j] if j < len(ocr_data.get("conf", [])) else "-1"
                try:
                    conf = float(conf_str) / 100.0
                except (ValueError, TypeError):
                    conf = 0.0
                confidences.append(conf)

        full_text = " ".join(text_parts)
        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )

        doc_id = uuid.uuid4().hex[:16]
        meta_dict = dict(base_meta)
        meta_dict.update({
            "document_id": doc_id,
            "source_path": str(source_path),
            "mime_type": "application/pdf",
            "parser_used": "ocr_local",
            "parser_version": self._version,
            "page_number": page_num,
            "section_path": [],
            "element_type": "paragraph",
            "confidence": round(avg_confidence, 4),
            "parsing_duration_ms": 0,
        })

        warnings: list[str] = []
        if avg_confidence < 0.3:
            warnings.append(
                f"Low OCR confidence ({avg_confidence:.2f}) on page {page_num}"
            )
        meta_dict["warnings"] = warnings

        return [
            Document(
                content=full_text if full_text else "[EMPTY - No text extracted]",
                meta=meta_dict,
            )
        ]
