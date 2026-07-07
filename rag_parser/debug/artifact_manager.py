from __future__ import annotations

import html
import io
import uuid
from pathlib import Path
from typing import Any

from haystack import Document
from PIL import Image, ImageDraw, ImageFont

from rag_parser.config import config
from rag_parser.logging_setup import get_logger

logger = get_logger(__name__)


class DebugArtifactManager:
    """Generates and manages debug artifacts for OCR-based parses.

    For each document parsed via OCR, this produces:
    - Page images (rasterized from PDF)
    - Overlay images (OCR text overlaid on source page)
    - An HTML report with per-page confidence and side-by-side views
    """

    def __init__(self, enabled: bool | None = None) -> None:
        self._enabled = (
            enabled if enabled is not None else config.enable_debug
        )
        self._base_dir = config.debug_path

    def create_parse_debug(
        self,
        document_id: str,
        page_images: list[Image.Image],
        ocr_texts: list[str],
        confidences: list[float],
        source_path: str,
    ) -> Path:
        """Create debug artifacts for a parsed document.

        Returns the path to the HTML report.
        """
        if not self._enabled:
            return self._base_dir

        doc_dir = self._base_dir / document_id
        doc_dir.mkdir(parents=True, exist_ok=True)

        pages_dir = doc_dir / "pages"
        pages_dir.mkdir(exist_ok=True)

        overlay_dir = doc_dir / "overlays"
        overlay_dir.mkdir(exist_ok=True)

        page_entries: list[dict[str, Any]] = []

        for i, (img, text, conf) in enumerate(
            zip(page_images, ocr_texts, confidences)
        ):
            page_path = pages_dir / f"page_{i:04d}.png"
            img.save(page_path)

            overlay_path = overlay_dir / f"page_{i:04d}_overlay.png"
            self._create_overlay(img, text, overlay_path)

            page_entries.append(
                {
                    "page": i,
                    "image": str(page_path.relative_to(self._base_dir)),
                    "overlay": str(
                        overlay_path.relative_to(self._base_dir)
                    ),
                    "confidence": round(conf, 4),
                    "text_length": len(text),
                    "text_preview": text[:200],
                }
            )

        report_path = doc_dir / "report.html"
        self._write_report(
            report_path, document_id, source_path, page_entries
        )

        logger.info(
            "Debug artifacts created",
            document_id=document_id,
            pages=len(page_entries),
            report_path=str(report_path),
        )

        return report_path

    def get_debug_report(self, document_id: str) -> str | None:
        """Get the path to an existing debug report for a document."""
        report_path = self._base_dir / document_id / "report.html"
        if report_path.exists():
            return str(report_path)
        return None

    def _create_overlay(
        self,
        image: Image.Image,
        text: str,
        output_path: Path,
    ) -> None:
        """Create an image with OCR text overlaid on the original."""
        overlay = image.copy().convert("RGBA")
        txt_layer = Image.new("RGBA", overlay.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        try:
            font = ImageFont.truetype(
                "/System/Library/Fonts/Helvetica.ttc", 16
            )
        except (IOError, OSError):
            font = ImageFont.load_default()

        margin = 10
        y = margin
        max_w = overlay.width - 2 * margin
        line_height = 20

        for line in text.split("\n")[:100]:
            words = line.split()
            x = margin
            for word in words:
                try:
                    bbox = draw.textbbox((x, y), word, font=font)
                    w = bbox[2] - bbox[0]
                except Exception:
                    w = len(word) * 8

                if x + w > max_w:
                    x = margin
                    y += line_height

                if y > overlay.height - margin:
                    break

                draw.text((x, y), word, fill=(0, 0, 255, 160), font=font)
                x += w + 5

            y += line_height
            if y > overlay.height - margin:
                break

        combined = Image.alpha_composite(overlay, txt_layer)
        combined.convert("RGB").save(output_path)

    def _write_report(
        self,
        path: Path,
        document_id: str,
        source_path: str,
        pages: list[dict[str, Any]],
    ) -> None:
        """Write an HTML debug report."""
        rows = ""
        for p in pages:
            rows += f"""
            <tr>
                <td>{p['page']}</td>
                <td>{p['confidence']}</td>
                <td>{p['text_length']}</td>
                <td><pre>{html.escape(p['text_preview'])}</pre></td>
                <td>
                    <img src="../{p['image']}" width="200" />
                    <img src="../{p['overlay']}" width="200" />
                </td>
            </tr>"""

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Debug: {document_id}</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 2em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
  th {{ background: #f5f5f5; }}
  img {{ max-width: 300px; }}
  pre {{ max-height: 100px; overflow: auto; font-size: 11px; }}
</style></head><body>
<h1>Debug Report: {html.escape(document_id)}</h1>
<p>Source: {html.escape(source_path)}</p>
<table>
<tr><th>Page</th><th>Confidence</th><th>Chars</th><th>Text Preview</th><th>Image / Overlay</th></tr>
{rows}
</table></body></html>"""

        path.write_text(html_content)
