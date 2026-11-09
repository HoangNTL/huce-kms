import io
import logging
from pathlib import Path

import pymupdf

from api.core.exceptions import BadRequestException

logger = logging.getLogger("huce_kms.rag.parser")


class DocumentParser:
    """Extracts text content and page metadata from supported document files."""

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> list[dict[str, int | str]]:
        """Extract text page by page from PDF bytes."""
        try:
            pages: list[dict[str, int | str]] = []
            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    text = page.get_text("text").strip()
                    if text:
                        pages.append({
                            "page_number": page_index + 1,
                            "text": text,
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
