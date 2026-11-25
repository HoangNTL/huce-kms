import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import pymupdf

from api.core.exceptions import BadRequestException
from api.services.ai.managers.ocr_manager import ocr_manager
from api.services.rag.patterns import REPEATED_COMMA_RE
from api.services.rag.pdf_tables import extract_page_text_with_tables

logger = logging.getLogger("huce_kms.rag.parser")

_ALPHA_TOKEN_RE = re.compile(r"\b[A-Za-zÀ-ỹ]+\b")
_CONSONANT_ONLY_RE = re.compile(r"^[bcdfghklmnpqrstvwxzđ]+$")
_GARBLED_CID_RE = re.compile(r"(?:\ufffd|\(cid:\d+\))")
_CONSECUTIVE_SINGLE_CHAR_RE = re.compile(r"\b[A-Za-zÀ-ỹ]\s+[A-Za-zÀ-ỹ]\s+[A-Za-zÀ-ỹ]\b")
_ALLOWED_SHORT_TOKENS = frozenset({
    "a", "à", "á", "ả", "ã", "ạ", "ý", "ở", "ô", "ủ", "ờ",
    "km", "kg", "cm", "mm", "ml", "vs", "ms", "mr", "dr", "st", "tp",
    "gv", "sv", "vnd", "pdf", "url", "sql", "xml", "css", "php", "html", "http",
})


class DocumentParser:
    """Extracts text content and page metadata from supported document files (.pdf, .txt, .md)."""

    @staticmethod
    def _is_blank_pixmap(pix: pymupdf.Pixmap) -> bool:
        """Return True if rendered page pixmap is almost entirely white/uniform."""
        samples = pix.samples
        if not samples:
            return True
        sampled = samples[::16]
        return (sum(1 for b in sampled if b < 245) / max(1, len(sampled))) < 0.002

    @classmethod
    def _render_page_for_ocr(cls, page: pymupdf.Page) -> bytes | None:
        """Render a PDF page to compressed JPEG bytes, or return None if visually blank."""
        pix = page.get_pixmap(dpi=150)
        return None if cls._is_blank_pixmap(pix) else pix.tobytes("jpeg", jpg_quality=85)

    @staticmethod
    def _is_garbled_page_text(text: str) -> bool:
        """Detect corrupted OCR text layers or broken font mappings (e.g. 'b d h di', 'th uyế t')."""
        if not text or len(text.strip()) < 20:
            return False
        if (
            len(_GARBLED_CID_RE.findall(text)) >= 2
            or len(REPEATED_COMMA_RE.findall(text)) >= 2
            or len(_CONSECUTIVE_SINGLE_CHAR_RE.findall(text)) >= 2
        ):
            return True

        tokens = list(_ALPHA_TOKEN_RE.finditer(text))
        if len(tokens) < 25:
            return False

        bad_fragments = 0
        for m in tokens:
            tok = m.group(0)
            if not tok.islower() or tok in _ALLOWED_SHORT_TOKENS:
                continue
            start, end = m.start(), m.end()
            if (end < len(text) and text[end] in ")./") or (start > 0 and text[start - 1] == "/"):
                continue
            if start >= 2 and text[start - 2 : start].strip().isdigit():
                continue
            if len(tok) == 1 or _CONSONANT_ONLY_RE.match(tok):
                bad_fragments += 1

        return bad_fragments >= 8 and (bad_fragments / len(tokens)) >= 0.12

    @staticmethod
    def _extract_page_text_with_tables(page: pymupdf.Page) -> str:
        """Extract text and Markdown tables from a PDF page in top-to-bottom reading order."""
        return extract_page_text_with_tables(page)

    @staticmethod
    def _ensure_pdf_has_text(pages: list[dict[str, int | str]]) -> None:
        if not "".join(str(p["text"]).strip() for p in pages):
            raise BadRequestException(
                message=(
                    "Tài liệu là file PDF scan/ảnh và không có lớp văn bản điện tử (selectable text). "
                    "Hệ thống không thể trích xuất nội dung văn bản để lập chỉ mục."
                )
            )

    @classmethod
    def _classify_pdf_page(cls, page: pymupdf.Page) -> tuple[str, bool, bool]:
        """Extract page text and classify whether it is scanned or has a garbled text layer."""
        stripped_text = cls._extract_page_text_with_tables(page).strip()
        is_scanned = not stripped_text or (len(stripped_text) < 20 and len(page.get_images()) > 0)
        is_garbled = not is_scanned and cls._is_garbled_page_text(stripped_text)
        return ("" if is_scanned else stripped_text), is_scanned, is_garbled

    @classmethod
    def extract_text_from_pdf(cls, file_bytes: bytes) -> list[dict[str, int | str]]:
        """Extract text page by page from PDF bytes with table recognition (synchronous)."""
        try:
            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                pages = [
                    {"page_number": i + 1, "text": cls._classify_pdf_page(doc[i])[0]}
                    for i in range(len(doc))
                ]
            cls._ensure_pdf_has_text(pages)
            return pages
        except BadRequestException:
            raise
        except Exception as e:
            logger.error("Failed to parse PDF document: %s", e)
            raise BadRequestException(
                message=f"Failed to read PDF document or file is corrupted: {str(e)}"
            ) from e

    @staticmethod
    async def _ocr_cache_op(
        storage_service: Any | None,
        ocr_cache_key: str | None,
        cached_pages: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Load (when cached_pages is None) or persist per-page OCR checkpoint cache."""
        if not storage_service or not ocr_cache_key:
            return {}
        cache_object = f"ocr-cache/{ocr_cache_key}.json"
        if cached_pages is None:
            try:
                data = json.loads((await storage_service.get_file(cache_object)).decode("utf-8"))
                return {str(k): str(v) for k, v in data.items() if isinstance(v, str) and v.strip()} if isinstance(data, dict) else {}
            except FileNotFoundError:
                return {}
            except Exception as exc:
                logger.warning("Could not load OCR cache '%s': %s", cache_object, exc)
                return {}

        if not cached_pages:
            return cached_pages
        try:
            payload = json.dumps(cached_pages, ensure_ascii=False).encode("utf-8")
            await storage_service.upload_file(
                file_bytes=payload,
                object_name=cache_object,
                content_type="application/json; charset=utf-8",
            )
            logger.info("Saved OCR checkpoint cache '%s' (%d pages).", cache_object, len(cached_pages))
        except Exception as exc:
            logger.warning("Could not save OCR cache '%s': %s", cache_object, exc)
        return cached_pages

    @classmethod
    async def extract_text_from_pdf_async(
        cls,
        file_bytes: bytes,
        enable_ocr: bool = True,
        ocr_cache_key: str | None = None,
        storage_service: Any | None = None,
    ) -> list[dict[str, int | str]]:
        """Extract text from PDF, reusing per-page OCR cache and delegating missing pages to VisionOCRManager."""
        try:
            cached_pages = await cls._ocr_cache_op(storage_service, ocr_cache_key)
            cache_hits = 0
            pages: list[dict[str, int | str]] = []
            ocr_queue: list[tuple[int, bytes, bool]] = []

            with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
                for idx in range(len(doc)):
                    page = doc[idx]
                    text, is_scanned, is_garbled = cls._classify_pdf_page(page)
                    page_key = str(idx + 1)

                    if (is_scanned or is_garbled) and page_key in cached_pages:
                        pages.append({"page_number": idx + 1, "text": cached_pages[page_key]})
                        cache_hits += 1
                        continue

                    pages.append({"page_number": idx + 1, "text": text})
                    if (is_scanned or is_garbled) and enable_ocr and ocr_manager.has_available_provider():
                        img_bytes = await asyncio.to_thread(cls._render_page_for_ocr, page)
                        if img_bytes is not None:
                            if is_garbled:
                                logger.info("Detected corrupted text layer on PDF page %d; queuing Vision OCR fallback.", idx + 1)
                            ocr_queue.append((idx, img_bytes, is_scanned))
                        elif is_scanned:
                            logger.info("PDF page %d appears visually blank; skipping OCR.", idx + 1)

            if cache_hits:
                logger.info("Reused %d OCR-cached pages (key=%s); %d pages remaining.", cache_hits, ocr_cache_key, len(ocr_queue))

            if ocr_queue:
                logger.info("Detected %d / %d scanned or corrupted pages in PDF. Delegating to VisionOCRManager...", len(ocr_queue), len(pages))
                ocr_results = await ocr_manager.ocr_images_batch(
                    [(f"PDF page {i + 1}", img) for i, img, _ in ocr_queue], mime_type="image/jpeg"
                )
                failed_pages: list[int] = []
                cache_dirty = False
                for (page_idx, _, is_required), res in zip(ocr_queue, ocr_results, strict=False):
                    if isinstance(res, Exception):
                        if is_required:
                            failed_pages.append(page_idx + 1)
                            logger.error("OCR failed on PDF page %d: %s", page_idx + 1, res)
                        else:
                            logger.warning("Fallback OCR failed on garbled PDF page %d (%s); retaining repaired text.", page_idx + 1, res)
                    elif isinstance(res, str) and res.strip():
                        clean_res = res.strip()
                        pages[page_idx]["text"] = clean_res
                        cached_pages[str(page_idx + 1)] = clean_res
                        cache_dirty = True

                if cache_dirty:
                    await cls._ocr_cache_op(storage_service, ocr_cache_key, cached_pages)
                if failed_pages:
                    failed_str = ", ".join(str(p) for p in failed_pages)
                    raise BadRequestException(
                        message=(
                            f"OCR thất bại ở trang {failed_str} trong file PDF (có thể do giới hạn tốc độ API hoặc lỗi kết nối). "
                            "Vui lòng thử xử lý lại tài liệu để đảm bảo không bị mất nội dung."
                        )
                    )

            cls._ensure_pdf_has_text(pages)
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
        for encoding in ("utf-8", "latin-1"):
            try:
                text = file_bytes.decode(encoding).strip()
                return [{"page_number": 1, "text": text}] if text else []
            except UnicodeDecodeError:
                continue
        raise BadRequestException(message="Failed to decode text content (UTF-8 encoding required).")

    @staticmethod
    def _validate_suffix(file_name: str) -> str:
        suffix = Path(file_name).suffix.lower()
        if suffix not in (".pdf", ".txt", ".md"):
            raise BadRequestException(
                message=f"Unsupported file format '{suffix}'. Supported formats: .pdf, .txt, .md."
            )
        return suffix

    @classmethod
    def parse(cls, file_bytes: bytes, file_name: str) -> list[dict[str, int | str]]:
        """Parse document bytes based on file extension (synchronous)."""
        suffix = cls._validate_suffix(file_name)
        pages = cls.extract_text_from_pdf(file_bytes) if suffix == ".pdf" else cls.extract_text_from_plain_text(file_bytes)
        if not pages:
            raise BadRequestException(message="Document contains no text content to process.")
        return pages

    @classmethod
    async def parse_async(
        cls,
        file_bytes: bytes,
        file_name: str,
        enable_ocr: bool = True,
        ocr_cache_key: str | None = None,
        storage_service: Any | None = None,
    ) -> list[dict[str, int | str]]:
        """Parse document bytes asynchronously with Vision OCR fallback and optional page cache."""
        suffix = cls._validate_suffix(file_name)
        pages = (
            await cls.extract_text_from_pdf_async(
                file_bytes, enable_ocr=enable_ocr, ocr_cache_key=ocr_cache_key, storage_service=storage_service
            )
            if suffix == ".pdf"
            else cls.extract_text_from_plain_text(file_bytes)
        )
        if not pages:
            raise BadRequestException(message="Document contains no text content to process.")
        return pages
