import asyncio
import io
import logging
from pathlib import Path

from google import genai
from google.genai import types
import pymupdf

from api.core.config import settings
from api.core.exceptions import BadRequestException

logger = logging.getLogger("huce_kms.rag.parser")


class DocumentParser:
    """Extracts text content and page metadata from supported document files."""

    @classmethod
    async def ocr_image_bytes(
        cls,
        image_bytes: bytes,
        mime_type: str = "image/png",
        client: genai.Client | None = None,
        semaphore: asyncio.Semaphore | None = None,
        context_label: str = "image",
    ) -> str:
        """Transcribe text from image bytes using Gemini Vision OCR."""
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not configured; skipping OCR for %s.", context_label)
            return ""

        client = client or genai.Client(api_key=settings.GEMINI_API_KEY)

        async def _run_ocr() -> str:
            try:
                part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                prompt = (
                    "Bạn là hệ thống trích xuất văn bản (OCR) chính xác cao cho tài liệu học thuật và văn bản hành chính Việt Nam.\n"
                    "Hãy đọc và trích xuất toàn bộ nội dung văn bản trên hình ảnh này.\n"
                    "Yêu cầu:\n"
                    "1. Giữ nguyên cấu trúc, tiêu đề, số thứ tự, số hiệu văn bản, các Điều/Khoản.\n"
                    "2. Nếu có bảng biểu, hãy chuyển đổi chính xác thành định dạng Markdown Table.\n"
                    "3. Nếu hình ảnh không chứa văn bản (ảnh phong cảnh, logo đơn thuần, ảnh sự kiện không có văn bản), chỉ trả về chuỗi rỗng, không giải thích hay bình luận.\n"
                    "4. Chỉ trả về nội dung văn bản trích xuất được, không kèm lời mở đầu, giải thích hay bình luận."
                )

                max_retries = 2
                for attempt in range(max_retries):
                    try:
                        response = await client.aio.models.generate_content(
                            model=settings.LLM_MODEL,
                            contents=[part, prompt],
                        )
                        extracted = response.text.strip() if response.text else ""
                        logger.info(
                            "Gemini OCR successfully processed %s (%d characters extracted).",
                            context_label,
                            len(extracted),
                        )
                        return extracted
                    except Exception as exc:
                        if attempt < max_retries - 1:
                            logger.warning(
                                "Gemini OCR attempt %d failed on %s: %s. Retrying in 1.5s...",
                                attempt + 1,
                                context_label,
                                exc,
                            )
                            await asyncio.sleep(1.5)
                        else:
                            logger.warning(
                                "Gemini OCR failed on %s after %d attempts: %s",
                                context_label,
                                max_retries,
                                exc,
                            )
                            return ""
            except Exception as e:
                logger.warning("Gemini OCR preparation failed on %s: %s", context_label, e)
                return ""

        if semaphore:
            async with semaphore:
                return await _run_ocr()
        return await _run_ocr()

    @classmethod
    async def _ocr_page_with_gemini(
        cls,
        page: pymupdf.Page,
        client: genai.Client,
        semaphore: asyncio.Semaphore | None = None,
    ) -> str:
        """Render a PDF page to image and transcribe text using Gemini Vision."""
        try:
            def _render_page_png() -> bytes:
                pix = page.get_pixmap(dpi=150)
                return pix.tobytes("png")

            image_bytes = await asyncio.to_thread(_render_page_png)
            return await cls.ocr_image_bytes(
                image_bytes=image_bytes,
                mime_type="image/png",
                client=client,
                semaphore=semaphore,
                context_label=f"PDF page {page.number + 1}",
            )
        except Exception as e:
            logger.warning("Gemini OCR rendering failed on page %d: %s", page.number + 1, e)
            return ""

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
        """Extract text page by page from PDF bytes with table recognition (synchronous)."""
        try:
            pages: list[dict[str, int | str]] = []
            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    text = cls._extract_page_text_with_tables(page)
                    pages.append({
                        "page_number": page_index + 1,
                        "text": text.strip() if text else "",
                    })

            total_content = "".join(str(p["text"]).strip() for p in pages)
            if not total_content:
                raise BadRequestException(
                    message=(
                        "Tài liệu là file PDF scan/ảnh và không có lớp văn bản điện tử (selectable text). "
                        "Hệ thống không thể trích xuất nội dung văn bản."
                    )
                )

            return pages
        except BadRequestException:
            raise
        except Exception as e:
            logger.error("Failed to parse PDF document: %s", e)
            raise BadRequestException(
                message=f"Failed to read PDF document or file is corrupted: {str(e)}"
            ) from e

    @classmethod
    async def extract_text_from_pdf_async(
        cls, file_bytes: bytes, enable_ocr: bool = True
    ) -> list[dict[str, int | str]]:
        """Extract text from PDF with asynchronous Gemini Vision OCR fallback for scanned pages."""
        try:
            pages: list[dict[str, int | str]] = []
            scanned_pages_to_ocr: list[tuple[int, pymupdf.Page]] = []

            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                for page_index in range(len(doc)):
                    page = doc[page_index]
                    text = cls._extract_page_text_with_tables(page)
                    # If page text is empty or negligible, mark as scanned candidate
                    if not text.strip():
                        scanned_pages_to_ocr.append((page_index, page))
                        pages.append({"page_number": page_index + 1, "text": ""})
                    else:
                        pages.append({"page_number": page_index + 1, "text": text.strip()})

                # If scanned pages detected and OCR is enabled and API key is configured
                if scanned_pages_to_ocr and enable_ocr and settings.GEMINI_API_KEY:
                    logger.info(
                        "Detected %d / %d scanned pages without text layer in PDF. Initiating Gemini Vision OCR...",
                        len(scanned_pages_to_ocr),
                        len(doc),
                    )
                    client = genai.Client(api_key=settings.GEMINI_API_KEY)
                    semaphore = asyncio.Semaphore(4)  # Concurrency limit to prevent rate limiting

                    tasks = [
                        cls._ocr_page_with_gemini(page, client, semaphore)
                        for _, page in scanned_pages_to_ocr
                    ]
                    ocr_results = await asyncio.gather(*tasks, return_exceptions=True)

                    for (page_idx, _), res in zip(scanned_pages_to_ocr, ocr_results, strict=False):
                        if isinstance(res, str) and res.strip():
                            pages[page_idx]["text"] = res.strip()

            # Verify that document contains actual readable text
            total_content = "".join(str(p["text"]).strip() for p in pages)
            if not total_content:
                raise BadRequestException(
                    message=(
                        "Tài liệu là file PDF scan/ảnh và không có lớp văn bản điện tử (selectable text). "
                        "Hệ thống không thể trích xuất nội dung văn bản để lập chỉ mục."
                    )
                )

            return pages
        except BadRequestException:
            raise
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
        """Parse document bytes based on file extension (synchronous)."""
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

    @classmethod
    async def parse_async(
        cls, file_bytes: bytes, file_name: str, enable_ocr: bool = True
    ) -> list[dict[str, int | str]]:
        """Parse document bytes asynchronously with OCR fallback for scanned documents."""
        suffix = Path(file_name).suffix.lower()

        if suffix == ".pdf":
            pages = await cls.extract_text_from_pdf_async(file_bytes, enable_ocr=enable_ocr)
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
