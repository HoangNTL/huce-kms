import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import update

from api.constants.enums import DocumentSourceType, DocumentStatus
from api.core.config import settings
from api.core.database import uuid7
from api.models.crawl_session import CrawlSessionItem
from api.models.document import Document
from api.repositories.category import CategoryRepository
from api.repositories.document import DocumentRepository
from api.services.crawler.ingestion.reader import CrawlArtifactReader
from api.services.crawler.ingestion.schemas import (
    IngestItemResult,
    IngestSummaryResponse,
)
from api.services.document import DocumentService

logger = logging.getLogger(__name__)


class CrawlIngestionAdapter:
    """Bridges Crawl Artifacts into HUCE-KMS Document management and RAG indexing."""

    def __init__(
        self,
        document_service: DocumentService,
        document_repo: DocumentRepository,
        category_repo: CategoryRepository | None = None,
    ):
        self.document_service = document_service
        self.document_repo = document_repo
        self.category_repo = category_repo

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Compute SHA-256 hash."""
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    @staticmethod
    def is_meaningful_markdown(content: str, min_text_chars: int = 40) -> bool:
        """
        Check if markdown content contains substantive text beyond metadata header,
        headings, dates, view counters, and download links.
        """
        if not content or not content.strip():
            return False

        # If it has OCR text section, it is substantive
        if "## Nội dung trích xuất từ văn bản đính kèm" in content:
            return True

        # Remove header section (starts with # Title ... up to ---)
        body = re.sub(
            r"^#\s+[^\n]+\n+(?:- \*\*[^\n]+\n+)*---\s*",
            "",
            content.strip(),
            flags=re.MULTILINE,
        )

        # Remove image tags: ![alt](url)
        body = re.sub(r"!\[.*?\]\(.*?\)", "", body)

        # Remove file/attachment links: [text](url)
        body = re.sub(r"\[.*?\]\(.*?\)", "", body)

        # Remove standalone URLs
        body = re.sub(r"https?://\S+", "", body)

        # Remove headings: #, ##, ###, ####, #####, ######
        body = re.sub(r"^\s*#{1,6}\s+.*$", "", body, flags=re.MULTILINE)

        # Remove date and view count patterns
        body = re.sub(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", "", body)
        body = re.sub(r"(?:Lượt\s+xem|Xem|Ngày\s+đăng)\s*:\s*\d+", "", body, flags=re.IGNORECASE)

        # Remove markdown horizontal rules & formatting chars
        body = re.sub(r"[-*_~`#|]", " ", body)

        # Clean remaining whitespace and check meaningful text length
        cleaned_text = re.sub(r"\s+", " ", body).strip()
        return len(cleaned_text) >= min_text_chars

    @staticmethod
    def is_scanned_document_image(img_path: Path) -> bool:
        """
        Detect if an image is likely a scanned document sheet (e.g. A4 notice, official decision)
        versus a landscape illustration photo, banner, or activity snapshot.
        """
        try:
            if not img_path.exists() or img_path.stat().st_size < 40 * 1024:
                return False

            import pymupdf

            with pymupdf.open(str(img_path)) as doc:
                if len(doc) == 0:
                    return False
                rect = doc[0].rect
                if rect.width <= 0 or rect.height <= 0:
                    return False

                # Vertical A4 sheet has aspect ratio height/width ~ 1.41
                aspect_ratio = rect.height / rect.width
                is_portrait = aspect_ratio >= 1.15
                has_doc_dimensions = rect.height >= 500

                return is_portrait and has_doc_dimensions
        except Exception:
            return False

    @staticmethod
    def _has_ocr_provider() -> bool:
        from api.services.ai.managers.ocr_manager import ocr_manager

        return ocr_manager.has_available_provider()

    async def enrich_markdown_with_ocr(
        self,
        markdown_content: str,
        image_files: list[Path],
    ) -> str:
        """If markdown has image attachments and is not yet enriched, transcribe them via Gemini Vision OCR."""
        if not image_files or not self._has_ocr_provider():
            return markdown_content

        if "## Nội dung trích xuất từ văn bản đính kèm" in markdown_content:
            return markdown_content

        # Filter: only transcribe images that match scanned document geometry (A4 portrait)
        candidate_scans = [img for img in image_files if self.is_scanned_document_image(img)]
        if not candidate_scans:
            logger.info(
                "No scanned document candidates detected among %d image attachments; skipping OCR.",
                len(image_files),
            )
            return markdown_content

        try:
            from api.services.ai.managers.ocr_manager import ocr_manager

            mime_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }

            ocr_sections = []
            for img_path in candidate_scans:
                try:
                    img_bytes = img_path.read_bytes()
                    mime = mime_types.get(img_path.suffix.lower(), "image/png")
                    extracted_text = await ocr_manager.ocr_image_bytes(
                        image_bytes=img_bytes,
                        mime_type=mime,
                        context_label=f"scanned document '{img_path.name}'",
                    )
                    if extracted_text and len(extracted_text.strip()) > 40:
                        ocr_sections.append(
                            f"### Văn bản trích xuất từ ảnh ({img_path.name}):\n\n{extracted_text.strip()}"
                        )
                except Exception as e:
                    logger.warning("Failed to OCR image attachment '%s': %s", img_path.name, e)

            if ocr_sections:
                return (
                    f"{markdown_content.strip()}\n\n---\n\n## Nội dung trích xuất từ văn bản đính kèm (Ảnh scan)\n\n"
                    + "\n\n".join(ocr_sections)
                    + "\n"
                )
        except Exception as e:
            logger.warning("OCR enrichment during ingestion failed: %s", e)

        return markdown_content

    async def ingest_page(
        self,
        page_dir: Path,
        category_id: UUID | None = None,
        auto_publish: bool = False,
        created_by_id: UUID | None = None,
        uploader_id: UUID | None = None,
    ) -> list[IngestItemResult]:
        """Ingest a single page's Markdown and attached PDFs into the document system."""
        actual_creator_id = created_by_id or uploader_id
        payload = CrawlArtifactReader.read_page(page_dir)
        results: list[IngestItemResult] = []

        # 1. Enrich Markdown with OCR from scanned images if present
        enriched_markdown = payload.markdown_content
        if payload.image_files:
            enriched_markdown = await self.enrich_markdown_with_ocr(
                markdown_content=payload.markdown_content,
                image_files=payload.image_files,
            )

        # 2. Process Markdown Document (filter out empty/stub wrapper pages)
        md_result: IngestItemResult | None = None
        if self.is_meaningful_markdown(enriched_markdown):
            md_bytes = enriched_markdown.encode("utf-8")
            md_name = f"{page_dir.name}_content.md"
            md_title = payload.metadata.content.title.strip() or f"Bài viết {payload.metadata.source.url}"
            md_result = await self._ingest_file(
                file_bytes=md_bytes,
                file_name=md_name,
                title=md_title,
                file_type="md",
                source_url=payload.metadata.source.url,
                category_id=category_id,
                created_by_id=actual_creator_id,
                auto_publish=auto_publish,
            )
            results.append(md_result)
        else:
            logger.info(
                "Skipping stub markdown for page '%s' (no substantive text content to index).",
                page_dir.name,
            )
            results.append(
                IngestItemResult(
                    title=payload.metadata.content.title.strip() or f"Bài viết {payload.metadata.source.url}",
                    file_name=f"{page_dir.name}_content.md",
                    file_type="md",
                    source_url=payload.metadata.source.url,
                    status="skipped",
                    chunks_count=0,
                    error="Bỏ qua do file Markdown chỉ chứa thông tin vỏ bọc / link đính kèm (không có nội dung văn bản thực chất để lập chỉ mục).",
                )
            )

        parent_doc_id = md_result.document_id if md_result and md_result.document_id else None

        # 3. Process Attached PDFs
        for pdf_path in payload.pdf_files:
            try:
                pdf_bytes = pdf_path.read_bytes()
                raw_pdf_title = f"{payload.metadata.content.title.strip()} - Phụ lục ({pdf_path.name})"
                pdf_title = (raw_pdf_title[:251] + "...") if len(raw_pdf_title) > 255 else raw_pdf_title
                pdf_result = await self._ingest_file(
                    file_bytes=pdf_bytes,
                    file_name=pdf_path.name,
                    title=pdf_title,
                    file_type="pdf",
                    source_url=payload.metadata.source.url,
                    category_id=category_id,
                    created_by_id=actual_creator_id,
                    auto_publish=auto_publish,
                )
                results.append(pdf_result)
            except Exception as e:
                logger.error("Failed to ingest PDF '%s': %s", pdf_path, e, exc_info=True)
                results.append(
                    IngestItemResult(
                        title=f"Phụ lục {pdf_path.name}"[:255],
                        file_name=pdf_path.name[:255],
                        file_type="pdf",
                        source_url=payload.metadata.source.url,
                        status="failed",
                        error=str(e),
                    )
                )

        # 4. Process Attached Images as Assets of the Parent Document
        # Uploads genuine images to MinIO under: documents/crawler/{YYYY}/{MM}/{parent_doc_id}/assets/{clean_name}
        # Does NOT create duplicate rows in the PostgreSQL documents table.
        uploaded_assets: list[dict[str, Any]] = []
        parent_file_path = md_result.file_path if md_result and md_result.file_path else None
        if payload.image_files and (parent_doc_id or parent_file_path):
            if parent_file_path:
                parent_dir = str(Path(parent_file_path).parent).replace("\\", "/")
            else:
                now_utc = datetime.now(timezone.utc)
                parent_dir = f"documents/crawler/{now_utc.year:04d}/{now_utc.month:02d}/{parent_doc_id}"
            asset_prefix = f"{parent_dir}/assets"

            for img_path in payload.image_files:
                try:
                    if not img_path.exists() or img_path.stat().st_size < 10 * 1024:
                        continue
                    clean_name = Path(img_path.name).name or "image.jpg"
                    if len(clean_name) > 255:
                        ext = Path(clean_name).suffix
                        clean_name = clean_name[: 255 - len(ext)] + ext

                    ext = Path(clean_name).suffix.lower()
                    content_type_map = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                    }
                    content_type = content_type_map.get(ext, "image/jpeg")
                    asset_key = f"{asset_prefix}/{clean_name}"

                    saved_asset_key = await self.document_service.storage_service.upload_file(
                        file_bytes=img_path.read_bytes(),
                        object_name=asset_key,
                        content_type=content_type,
                    )
                    uploaded_assets.append({
                        "file_name": clean_name,
                        "storage_key": saved_asset_key,
                        "is_scan": self.is_scanned_document_image(img_path),
                    })
                except Exception as img_err:
                    logger.warning(
                        "Could not upload image asset '%s' for document %s: %s",
                        img_path.name,
                        parent_doc_id,
                        img_err,
                    )

        # 5. Write ingestion record for inspection
        now_iso = datetime.now(timezone.utc).isoformat()
        now_dt = datetime.now(timezone.utc)
        ingestion_record_path = page_dir / "ingestion.json"
        try:
            with open(ingestion_record_path, "w", encoding="utf-8") as f:
                json.dump({
                    "ingested_at": now_iso,
                    "category_id": str(category_id) if category_id else None,
                    "documents": [r.model_dump(mode="json") for r in results],
                    "assets": uploaded_assets,
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Could not write ingestion record for %s: %s", page_dir.name, e)

        # 6. Sync ingestion status to database crawl_session_items only if at least one document succeeded
        has_successful_doc = any(r.status in ("uploaded", "indexed") for r in results)
        if has_successful_doc:
            try:
                stmt = (
                    update(CrawlSessionItem)
                    .where(CrawlSessionItem.page_hash == page_dir.name)
                    .values(is_ingested=True, ingested_at=now_dt)
                )
                await self.document_repo.session.execute(stmt)
                await self.document_repo.session.commit()
            except Exception as db_sync_err:
                logger.debug("Could not update crawl_session_item for %s: %s", page_dir.name, db_sync_err)

        return results

    async def _ingest_file(
        self,
        file_bytes: bytes,
        file_name: str,
        title: str,
        file_type: str,
        source_url: str,
        category_id: UUID | None = None,
        created_by_id: UUID | None = None,
        auto_publish: bool = False,
        uploader_id: UUID | None = None,
    ) -> IngestItemResult:
        actual_creator_id = created_by_id or uploader_id
        file_hash = self.compute_sha256(file_bytes)

        # Truncate title and file_name if exceeding database column limits (255)
        safe_title = (title or "Untitled").strip()
        if len(safe_title) > 255:
            safe_title = safe_title[:251] + "..."

        safe_file_name = Path(file_name).name or "document"
        if len(safe_file_name) > 255:
            ext = Path(safe_file_name).suffix
            safe_file_name = safe_file_name[: 255 - len(ext)] + ext

        # 1. Check duplicate by file content hash
        existing = await self.document_repo.get_by_file_hash(file_hash)
        if existing:
            logger.info("Document already exists (hash=%s, id=%s), skipping.", file_hash, existing.id)
            return IngestItemResult(
                document_id=existing.id,
                title=safe_title,
                file_name=safe_file_name,
                file_type=file_type,
                source_url=source_url,
                status="skipped",
                chunks_count=getattr(existing, "chunk_count", 0),
                error="Already exists in system (content hash match)",
            )

        # 2. Check duplicate by source URL and document identity
        if source_url:
            existing_by_url = await self.document_repo.get_by_source_url(source_url)
            for d in existing_by_url:
                if d.file_type == file_type and (d.file_name == safe_file_name or d.title == safe_title):
                    logger.info("Document from source_url '%s' already exists (id=%s), skipping.", source_url, d.id)
                    return IngestItemResult(
                        document_id=d.id,
                        title=safe_title,
                        file_name=safe_file_name,
                        file_path=d.file_path,
                        file_type=file_type,
                        source_url=source_url,
                        status="skipped",
                        chunks_count=getattr(d, "chunk_count", 0),
                        error="Already exists in system (source URL match)",
                    )

        # Map content types accurately
        clean_file_name = safe_file_name
        suffix = Path(safe_file_name).suffix.lower()
        if not suffix:
            suffix = f".{file_type}" if file_type else ".txt"

        content_type_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        content_type = content_type_map.get(suffix, "application/octet-stream")
        now_utc = datetime.now(timezone.utc)
        doc_id = uuid7()

        if auto_publish:
            # Full RAG Ingestion Pipeline for text and PDF
            doc_resp = await self.document_service.upload_and_process_document(
                file_bytes=file_bytes,
                file_name=safe_file_name,
                title=safe_title,
                category_id=category_id,
                created_by_id=actual_creator_id,
                source_url=source_url,
                source_type="crawler",
            )
            return IngestItemResult(
                document_id=doc_resp.id,
                title=doc_resp.title,
                file_name=doc_resp.file_name,
                file_path=doc_resp.file_path,
                file_type=file_type,
                source_url=source_url,
                status="indexed",
                chunks_count=doc_resp.chunk_count,
            )
        else:
            # Staging / Draft Mode with standardized hierarchical MinIO path:
            # documents/crawler/{YYYY}/{MM}/{document_id}/{clean_file_name}
            object_key = f"documents/crawler/{now_utc.year:04d}/{now_utc.month:02d}/{doc_id}/{clean_file_name}"

            saved_file_key = await self.document_service.storage_service.upload_file(
                file_bytes=file_bytes,
                object_name=object_key,
                content_type=content_type,
            )

            doc = Document(
                id=doc_id,
                title=safe_title,
                file_name=clean_file_name,
                file_path=saved_file_key,
                file_size=len(file_bytes),
                file_type=file_type,
                file_hash=file_hash,
                source_url=source_url,
                source_type=DocumentSourceType.CRAWLER,
                status=DocumentStatus.UPLOADED,
                category_id=category_id,
                created_by_id=actual_creator_id,
                total_pages=1,
                chunk_count=0,
                error_message=None,
            )
            try:
                created_doc = await self.document_repo.create(doc)
                await self.document_repo.session.commit()
            except Exception:
                await self.document_repo.session.rollback()
                try:
                    await self.document_service.storage_service.delete_file(saved_file_key)
                except Exception:
                    pass
                raise

            return IngestItemResult(
                document_id=created_doc.id,
                title=created_doc.title,
                file_name=created_doc.file_name,
                file_path=created_doc.file_path,
                file_type=file_type,
                source_url=source_url,
                status="uploaded",
                chunks_count=0,
            )

    async def ingest_session(
        self,
        session_dir: Path,
        category_id: UUID | None = None,
        auto_publish: bool = False,
        created_by_id: UUID | None = None,
        uploader_id: UUID | None = None,
    ) -> IngestSummaryResponse:
        """Ingest all successfully crawled pages in a session."""
        actual_creator_id = created_by_id or uploader_id
        payloads = CrawlArtifactReader.read_session(session_dir)
        all_items: list[IngestItemResult] = []

        for p in payloads:
            try:
                page_results = await self.ingest_page(
                    page_dir=p.page_dir,
                    category_id=category_id,
                    auto_publish=auto_publish,
                    created_by_id=actual_creator_id,
                )
                all_items.extend(page_results)
            except Exception as e:
                logger.error("Failed to ingest page '%s': %s", p.page_dir, e, exc_info=True)
                all_items.append(
                    IngestItemResult(
                        title=p.metadata.content.title,
                        file_name="page",
                        file_type="unknown",
                        source_url=p.metadata.source.url,
                        status="failed",
                        error=str(e),
                    )
                )

        successful = sum(1 for it in all_items if it.status in ("uploaded", "indexed"))
        skipped = sum(1 for it in all_items if it.status == "skipped")
        failed = sum(1 for it in all_items if it.status == "failed")

        return IngestSummaryResponse(
            total_pages=len(payloads),
            total_documents=len(all_items),
            successful=successful,
            skipped=skipped,
            failed=failed,
            items=all_items,
        )
