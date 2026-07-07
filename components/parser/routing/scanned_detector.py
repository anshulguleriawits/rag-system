from __future__ import annotations

from pathlib import Path

from components.parser.config import config
from components.parser.logging_setup import get_logger

logger = get_logger(__name__)


def is_scanned_pdf(path: Path | str) -> bool:
    """Detect if a PDF is scanned (image-only) by checking text layer density.

    Uses pypdf to extract text per page. If the ratio of non-empty pages
    or total character count is below the configured threshold, the PDF
    is considered scanned.

    This is a heuristic — PDFs with very little text (e.g. a single title)
    may be misclassified, which is acceptable because the user can always
    override the strategy explicitly.
    """
    path = Path(path)
    if path.suffix.lower() != ".pdf" or not path.exists():
        return False

    try:
        import pypdf

        reader = pypdf.PdfReader(str(path))
        total_chars = 0
        empty_pages = 0
        num_pages = len(reader.pages)

        if num_pages == 0:
            return False

        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            total_chars += len(text)
            if not text:
                empty_pages += 1

        # If most pages have no text, it's scanned
        empty_ratio = empty_pages / num_pages
        total_chars_per_page = total_chars / num_pages

        is_scanned = (
            empty_ratio > (1.0 - config.scanned_text_threshold)
            or total_chars_per_page < 50
        )

        logger.debug(
            "Scanned PDF detection",
            path=str(path),
            pages=num_pages,
            empty_pages=empty_pages,
            total_chars=total_chars,
            chars_per_page=round(total_chars_per_page, 1),
            is_scanned=is_scanned,
        )

        return is_scanned

    except ImportError:
        logger.warning(
            "pypdf not available, cannot detect scanned PDFs; "
            "assuming digital"
        )
        return False
    except Exception as e:
        logger.warning(
            "Error during scanned PDF detection",
            path=str(path),
            error=str(e),
        )
        return False
