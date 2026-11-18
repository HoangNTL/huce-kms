import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from api.core.database import uuid7
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

        # 1. Process Markdown Document
        if payload.markdown_content.strip():
            md_bytes = payload.markdown_content.encode("utf-8")
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

        # 2. Process Attached PDFs
        for pdf_path in payload.pdf_files:
            try:
                pdf_bytes = pdf_path.read_bytes()
                pdf_title = f"{payload.metadata.content.title.strip()} - Phụ lục ({pdf_path.name})"
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
                        title=f"Phụ lục {pdf_path.name}",
                        file_name=pdf_path.name,
                        file_type="pdf",
                        source_url=payload.metadata.source.url,
                        status="failed",
                        error=str(e),
                    )
                )

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

        # 1. Check duplicate by file content hash
        existing = await self.document_repo.get_by_file_hash(file_hash)
        if existing:
            logger.info("Document already exists (hash=%s, id=%s), skipping.", file_hash, existing.id)
            return IngestItemResult(
                document_id=existing.id,
                title=title,
                file_name=file_name,
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
                if d.file_type == file_type and (d.file_name == file_name or d.title == title):
                    logger.info("Document from source_url '%s' already exists (id=%s), skipping.", source_url, d.id)
                    return IngestItemResult(
                        document_id=d.id,
                        title=title,
                        file_name=file_name,
                        file_type=file_type,
                        source_url=source_url,
                        status="skipped",
                        chunks_count=getattr(d, "chunk_count", 0),
                        error="Already exists in system (source URL match)",
                    )

        if auto_publish:
            # Full RAG Ingestion Pipeline
            doc_resp = await self.document_service.upload_and_process_document(
                file_bytes=file_bytes,
                file_name=file_name,
                title=title,
                category_id=category_id,
                created_by_id=actual_creator_id,
                source_url=source_url,
                source_type="crawler",
            )
            return IngestItemResult(
                document_id=doc_resp.id,
                title=doc_resp.title,
                file_name=doc_resp.file_name,
                file_type=file_type,
                source_url=source_url,
                status="indexed",
                chunks_count=doc_resp.chunk_count,
            )
        else:
            # Staging / Draft Mode (Save record & file via StorageService, do NOT embed or push to Qdrant)
            clean_file_name = Path(file_name).name or "document"
            suffix = Path(file_name).suffix.lower()
            if not suffix:
                suffix = f".{file_type}" if file_type else ".txt"

            content_type_map = {
                ".pdf": "application/pdf",
                ".txt": "text/plain; charset=utf-8",
                ".md": "text/markdown; charset=utf-8",
            }
            content_type = content_type_map.get(suffix, "application/octet-stream")
            now_utc = datetime.now(timezone.utc)
            object_key = f"documents/{now_utc.strftime('%Y/%m')}/{uuid7()}{suffix}"

            saved_file_key = await self.document_service.storage_service.upload_file(
                file_bytes=file_bytes,
                object_name=object_key,
                content_type=content_type,
            )

            doc = Document(
                title=title,
                file_name=clean_file_name,
                file_path=saved_file_key,
                file_size=len(file_bytes),
                file_type=file_type,
                file_hash=file_hash,
                source_url=source_url,
                source_type="crawler",
                status="uploaded",
                category_id=category_id,
                created_by_id=actual_creator_id,
                total_pages=1,
                chunk_count=0,
                error_message=None,
            )
            created_doc = await self.document_repo.create(doc)
            return IngestItemResult(
                document_id=created_doc.id,
                title=created_doc.title,
                file_name=created_doc.file_name,
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
