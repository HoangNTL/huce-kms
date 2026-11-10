import io
import logging
from pathlib import Path

import pymupdf

from api.core.exceptions import BadRequestException

logger = logging.getLogger("huce_kms.rag.parser")


class DocumentParser:
    """Extracts text content and page metadata from supported document files."""

    @classmethod
    def _extract_page_text_with_tables(cls, page: pymupdf.Page) -> str:
        """
        Extract text from a PDF page, identifying and preserving tables in Markdown format.
        Combines non-table text blocks and markdown tables in top-to-bottom reading order.
        """
        try:
            tabs = page.find_tables()
        except Exception as e:
            logger.warning("Table detection failed on page %d: %s", page.number + 1, e)
            return page.get_text("text").strip()

        # If no tables found, return plain page text directly
        if not tabs or not tabs.tables:
            return page.get_text("text").strip()

        page_elements: list[tuple[float, str]] = []
        table_rects = [pymupdf.Rect(t.bbox) for t in tabs.tables]

        # 1. Add markdown tables
        for tab in tabs.tables:
            try:
                md_table = tab.to_markdown().strip()
                if md_table:
                    page_elements.append((tab.bbox[1], md_table))
            except Exception as e:
                logger.warning("Failed to convert table to markdown on page %d: %s", page.number + 1, e)

        # 2. Add text blocks that do not intersect with any detected table
        try:
            blocks = page.get_text("blocks")
            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if b[6] != 0:  # Skip image blocks
                    continue

                block_text = b[4].strip()
                if not block_text:
                    continue

                block_rect = pymupdf.Rect(b[:4])
                in_table = False
                for t_rect in table_rects:
                    if t_rect.intersects(block_rect):
                        intersection = t_rect & block_rect
                        # If more than 30% of block area is inside table bbox, skip it
                        if block_rect.get_area() > 0 and (intersection.get_area() / block_rect.get_area()) > 0.3:
                            in_table = True
                            break

                if not in_table:
                    page_elements.append((block_rect.y0, block_text))
        except Exception as e:
            logger.warning("Block extraction failed on page %d: %s", page.number + 1, e)

        # Sort all elements from top to bottom
        page_elements.sort(key=lambda item: item[0])
        result_text = "\n\n".join(item[1] for item in page_elements).strip()
        return result_text or page.get_text("text").strip()

    @classmethod
    def extract_text_from_pdf(cls, file_bytes: bytes) -> list[dict[str, int | str]]:
        """Extract text page by page from PDF bytes with table recognition."""
        try:
            pages: list[dict[str, int | str]] = []
            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    text = cls._extract_page_text_with_tables(page)
                    pages.append({
                        "page_number": page_index + 1,
                        "text": text if text else "[Page has no selectable text layer or is a scanned image]",
                    })
            return pages
        except Exception as e:
            logger.error("Failed to parse PDF document: %s", e)
            raise BadRequestException(
                message=f"Failed to read PDF document or file is corrupted: {str(e)}"
            ) from e

    @staticmethod
    def extract_text_from_plain_text(file_bytes: bytes) -> list[dict[str, int | str]]:
        """Decode plain text or markdown files."""
        try:
            text = file_bytes.decode("utf-8").strip()
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1").strip()
            except Exception as e:
                raise BadRequestException(
                    message="Failed to decode text content (UTF-8 encoding required)."
                ) from e

        return [{"page_number": 1, "text": text}] if text else []

    @classmethod
    def parse(cls, file_bytes: bytes, file_name: str) -> list[dict[str, int | str]]:
        """Parse document bytes based on file extension."""
        suffix = Path(file_name).suffix.lower()

        if suffix == ".pdf":
            pages = cls.extract_text_from_pdf(file_bytes)
        elif suffix in (".txt", ".md"):
            pages = cls.extract_text_from_plain_text(file_bytes)
        else:
            raise BadRequestException(
                message=f"Unsupported file format '{suffix}'. Supported formats: .pdf, .txt, .md."
            )

        if not pages:
            raise BadRequestException(
                message="Document contains no text content to process."
            )

        return pages
