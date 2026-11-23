import hashlib
import logging
import uuid
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from api.constants.enums import DocumentSourceType, DocumentStatus
from api.core.config import settings
from api.core.database import uuid7
from api.core.exceptions import (
    BadRequestException,
    ConflictException,
    EntityNotFoundException,
)
from api.models.document import Document
from api.models.document_chunk import DocumentChunk
from api.repositories.category import CategoryRepository
from api.repositories.document import DocumentRepository
from api.repositories.document_chunk import DocumentChunkRepository
from api.schemas.document import (
    DocumentDetailResponse,
    DocumentDownloadUrlResponse,
    DocumentResponse,
    DocumentUpdate,
)
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.rag.chunker import TextChunker
from api.services.rag.cleaner import TextCleaner
from api.services.rag.parser import DocumentParser
from api.services.rag.vector_store import QdrantVectorStore
from api.services.storage import StorageService, get_storage_service

logger = logging.getLogger("huce_kms.services.document")


class DocumentService:
    """Business logic service for document lifecycle management and RAG ingestion pipeline."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
        category_repo: CategoryRepository,
        embedder: EmbeddingManager,
        vector_store: QdrantVectorStore,
        storage_service: StorageService | None = None,
    ):
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.category_repo = category_repo
        self.embedder = embedder
        self.vector_store = vector_store
        self.storage_service = storage_service or get_storage_service()
        self.parser = DocumentParser()
        self.chunker = TextChunker(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        hasher.update(data)
        return hasher.hexdigest()

    async def upload_and_process_document(
        self,
        file_bytes: bytes,
        file_name: str,
        title: str,
        category_id: UUID | None = None,
        created_by_id: UUID | None = None,
        chunk_strategy: str = "legal_structural",
        uploader_id: UUID | None = None,
        source_url: str | None = None,
        source_type: DocumentSourceType | str = DocumentSourceType.UPLOAD,
    ) -> DocumentResponse:
        """Validate, store, parse, embed and index an uploaded document into PostgreSQL and Qdrant."""
        actual_creator_id = created_by_id or uploader_id
        # 1. Validate file extension
        suffix = Path(file_name).suffix.lower()
        if suffix not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(settings.ALLOWED_DOCUMENT_EXTENSIONS)
            raise BadRequestException(
                message=f"Unsupported file format '{suffix}'. Allowed formats: {allowed}."
            )

        # 2. Validate file size
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise BadRequestException(
                message=f"File size exceeds maximum allowed limit ({settings.MAX_UPLOAD_SIZE_MB}MB)."
            )

        # 3. Validate category existence if provided
        if category_id is not None:
            category = await self.category_repo.get_by_id(category_id)
            if not category:
                raise EntityNotFoundException(entity_name="Category", entity_id=category_id)

        # 4. Check for duplicate document content via SHA-256
        file_hash = self.compute_sha256(file_bytes)
        existing = await self.document_repo.get_by_file_hash(file_hash)
        if existing:
            raise ConflictException(
                message=f"Document already exists in the system (ID: {existing.id}, Title: '{existing.title}')."
            )

        # 5. Save file to Object Storage (MinIO) or local fallback
        clean_file_name = Path(file_name).name or "document"
        unique_file_name = f"{uuid.uuid4().hex[:12]}_{clean_file_name}"
        object_key = f"documents/{unique_file_name}"

        content_type_map = {
            ".pdf": "application/pdf",
            ".txt": "text/plain; charset=utf-8",
            ".md": "text/markdown; charset=utf-8",
        }
        content_type = content_type_map.get(suffix, "application/octet-stream")

        saved_file_key = await self.storage_service.upload_file(
            file_bytes=file_bytes,
            object_name=object_key,
            content_type=content_type,
        )

        # 6. Create preliminary Document record in PostgreSQL (status = 'pending')
        document = Document(
            title=title.strip(),
            file_name=clean_file_name,
            file_path=saved_file_key,
            file_size=len(file_bytes),
            file_type=suffix.lstrip("."),
            file_hash=file_hash,
            source_url=source_url,
            source_type=source_type if isinstance(source_type, DocumentSourceType) else DocumentSourceType.from_str(source_type),
            status=DocumentStatus.PENDING,
            category_id=category_id,
            created_by_id=actual_creator_id,
            total_pages=0,
            chunk_count=0,
            error_message=None,
        )
        document = await self.document_repo.create(document)

        # 7. Execute Ingestion Pipeline (Parsing -> Chunking -> Embedding -> Qdrant + DB Indexing)
        try:
            document = await self._execute_indexing_pipeline(
                document=document,
                file_bytes=file_bytes,
                file_name=file_name,
                chunk_strategy=chunk_strategy,
            )
        except Exception:
            # Remove stored file to avoid orphaned storage on upload failure
            try:
                await self.storage_service.delete_file(saved_file_key)
            except Exception as cleanup_err:
                logger.warning("Could not delete stored file '%s': %s", saved_file_key, cleanup_err)
            raise

        return await self._build_document_response(document)

    async def _execute_indexing_pipeline(
        self,
        document: Document,
        file_bytes: bytes,
        file_name: str,
        chunk_strategy: str = "legal_structural",
    ) -> Document:
        """Execute OCR/parsing, text cleaning, chunking, Gemini embedding, and Qdrant/PostgreSQL indexing."""
        document.status = DocumentStatus.PROCESSING
        await self.document_repo.update(document)

        try:
            # Step 1: Parse raw text pages (with automatic OCR for scanned PDFs)
            raw_pages = await self.parser.parse_async(file_bytes, file_name, enable_ocr=True)
            total_pages = len(raw_pages)

            # Step 2: Clean and normalize text
            cleaned_pages = TextCleaner.clean_pages(raw_pages)
            valid_pages = [p for p in cleaned_pages if str(p.get("cleaned_text", "")).strip()]
            if not valid_pages:
                raise BadRequestException(
                    message="Không tìm thấy nội dung văn bản hợp lệ trong tài liệu để trích xuất."
                )

            # Step 3: Chunk using structural legal strategy or configured strategy
            raw_chunks = TextChunker.chunk_with_strategy(
                pages=valid_pages,
                strategy=chunk_strategy,
                document_title=document.title,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            if not raw_chunks:
                raise BadRequestException(
                    message="No extractable text content found in document."
                )

            # Step 4: Clean previous chunks and vector points if re-processing
            await self.chunk_repo.delete_by_document_id(document.id)
            try:
                await self.vector_store.delete_by_document_id(document.id)
            except Exception as qdrant_err:
                logger.warning("Could not delete vector points for document id=%s: %s", document.id, qdrant_err)

            # Assign UUIDv7 to each chunk (for 1-1 mapping with Qdrant Point IDs)
            chunks_with_id = []
            for c in raw_chunks:
                chunk_dict = dict(c)
                chunk_dict["id"] = uuid7()
                chunk_dict["document_id"] = document.id
                chunk_dict["title"] = document.title
                chunk_dict["category_id"] = document.category_id
                chunks_with_id.append(chunk_dict)

            # Step 5: Generate vector embeddings and upsert to Qdrant
            texts_to_embed = [c["content"] for c in chunks_with_id]
            embeddings = await self.embedder.generate_embeddings_batch(texts_to_embed)
            await self.vector_store.upsert_chunks(chunks_with_id, embeddings)

            # Step 6: Persist chunks to PostgreSQL
            db_chunks = [
                DocumentChunk(
                    id=c["id"],
                    document_id=document.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    page_number=c["page_number"],
                    token_count=c["token_count"],
                )
                for c in chunks_with_id
            ]
            await self.chunk_repo.create_bulk(db_chunks)

            # Step 7: Mark document as successfully indexed
            document.status = DocumentStatus.INDEXED
            document.total_pages = total_pages
            document.chunk_count = len(chunks_with_id)
            document.error_message = None
            document = await self.document_repo.update(document)

            logger.info(
                "Document id=%s ('%s') successfully indexed with %d chunks and %d pages.",
                document.id,
                document.title,
                document.chunk_count,
                document.total_pages,
            )
            return document

        except Exception as e:
            logger.error("Failed to process document id=%s: %s", document.id, e)
            try:
                await self.vector_store.delete_by_document_id(document.id)
            except Exception as qdrant_err:
                logger.warning("Could not delete vector points for document id=%s: %s", document.id, qdrant_err)

            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            await self.document_repo.update(document)
            raise

    async def _build_document_response(self, document: Document) -> DocumentResponse:
        """Validate and enrich DocumentResponse with presigned download URL."""
        refreshed = await self.document_repo.get_with_category(document.id)
        resp = DocumentResponse.model_validate(refreshed or document)
        try:
            resp.download_url = await self.storage_service.get_presigned_download_url(
                object_name=document.file_path,
                original_filename=document.file_name,
            )
        except Exception as url_err:
            logger.warning("Could not generate presigned download URL for doc id=%s: %s", document.id, url_err)
        return resp

    async def process_document(
        self,
        document_id: UUID,
        chunk_strategy: str = "legal_structural",
    ) -> DocumentResponse:
        """Parse, clean, chunk, embed, and index an already uploaded document into PostgreSQL and Qdrant."""
        document = await self.document_repo.get_by_id(document_id)
        if not document:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)

        file_bytes = await self.storage_service.get_file(document.file_path)
        document = await self._execute_indexing_pipeline(
            document=document,
            file_bytes=file_bytes,
            file_name=document.file_name,
            chunk_strategy=chunk_strategy,
        )
        return await self._build_document_response(document)

    async def get_document_by_id(self, document_id: UUID) -> DocumentResponse:
        """Retrieve a document by ID with dynamic presigned download URL."""
        doc = await self.document_repo.get_with_category(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        return await self._build_document_response(doc)

    async def get_document_detail(self, document_id: UUID) -> DocumentDetailResponse:
        """Retrieve document metadata and all associated text chunks with download URL."""
        doc = await self.document_repo.get_with_chunks(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        resp = DocumentDetailResponse.model_validate(doc)
        try:
            resp.download_url = await self.storage_service.get_presigned_download_url(
                object_name=doc.file_path,
                original_filename=doc.file_name,
            )
        except Exception as e:
            logger.warning("Could not attach presigned download_url for doc detail id=%s: %s", document_id, e)
        return resp

    async def get_document_download_url(
        self, document_id: UUID, expiry_seconds: int = 3600
    ) -> DocumentDownloadUrlResponse:
        """Generate a presigned URL specifically for downloading or previewing a document."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        url = await self.storage_service.get_presigned_download_url(
            object_name=doc.file_path,
            expiry_seconds=expiry_seconds,
            original_filename=doc.file_name,
        )
        return DocumentDownloadUrlResponse(
            document_id=doc.id,
            file_name=doc.file_name,
            download_url=url,
            expires_in_seconds=expiry_seconds,
        )

    async def get_document_file_bytes(self, document_id: UUID) -> tuple[bytes, str, str]:
        """Retrieve the raw file bytes, filename, and content-type for a document."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        file_bytes = await self.storage_service.get_file(doc.file_path)
        content_type = "application/pdf" if doc.file_type == "pdf" else "text/plain; charset=utf-8"
        return file_bytes, doc.file_name, content_type

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 10,
        category_id: UUID | None = None,
        status: str | None = None,
        query: str | None = None,
    ) -> tuple[Sequence[DocumentResponse], int]:
        """List documents with pagination and filtering."""
        docs, total = await self.document_repo.search_with_count(
            skip=skip,
            limit=limit,
            category_id=category_id,
            status=status,
            query=query,
        )
        return [DocumentResponse.model_validate(d) for d in docs], total

    async def delete_document(self, document_id: UUID) -> None:
        """
        Soft-delete a document record and clean up associated search vectors.
        1. Hard-deletes vector points from Qdrant to ensure AI cannot retrieve deleted content.
        2. Retains the physical file in storage for compliance, audit, and recovery.
        3. Marks the document record as soft-deleted (deleted_at set) in PostgreSQL.
        """
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)

        # 1. Delete points in Qdrant Vector DB (prevent AI hallucinations / citation of deleted records)
        try:
            await self.vector_store.delete_by_document_id(document_id)
        except Exception as e:
            logger.warning("Failed to delete Qdrant points for document id=%s: %s", document_id, e)

        # 2. In soft-delete mode, physical storage file is preserved for retention/recovery

        # 3. Soft-delete Document record from PostgreSQL
        await self.document_repo.soft_delete(doc)
        logger.info("Soft-deleted document id=%s ('%s')", document_id, doc.title)

    async def restore_document(self, document_id: UUID) -> DocumentResponse:
        """
        Restore a soft-deleted document:
        1. Clears deleted_at in PostgreSQL.
        2. Re-indexes document chunks into Qdrant vector store.
        """
        doc = await self.document_repo.get_by_id(document_id, include_deleted=True)
        if not doc or doc.deleted_at is None:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)

        # 1. Restore record in PostgreSQL
        await self.document_repo.restore(doc)

        # 2. Re-index chunks into Qdrant
        doc_with_chunks = await self.document_repo.get_with_chunks(document_id)
        if doc_with_chunks and doc_with_chunks.chunks:
            try:
                chunk_texts = [c.content for c in doc_with_chunks.chunks]
                embed_res = await self.embedder.embed_texts(chunk_texts)
                embeddings = embed_res.embeddings
                points = [
                    {
                        "id": str(c.id),
                        "vector": emb,
                        "payload": {
                            "document_id": str(doc.id),
                            "chunk_index": c.chunk_index,
                            "content": c.content,
                            "token_count": c.token_count,
                            "page_number": c.page_number,
                            "heading_path": c.heading_path,
                            "category_id": str(doc.category_id) if doc.category_id else None,
                            "title": doc.title,
                        },
                    }
                    for c, emb in zip(doc_with_chunks.chunks, embeddings)
                ]
                await self.vector_store.upsert_chunks(points)
                logger.info("Re-indexed %d chunks into Qdrant for restored document id=%s", len(points), document_id)
            except Exception as e:
                logger.warning("Failed to re-index Qdrant points during document restore id=%s: %s", document_id, e)

        updated_doc = await self.document_repo.get_with_category(document_id)
        return DocumentResponse.model_validate(updated_doc or doc)

    async def update_document(
        self, document_id: UUID, payload: DocumentUpdate
    ) -> DocumentResponse:
        """Update document metadata (title and/or category) and sync to Qdrant."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)

        qdrant_payload: dict[str, Any] = {}

        # 1. Validate and update category if explicitly provided in payload
        if "category_id" in payload.model_fields_set:
            if payload.category_id is not None:
                cat = await self.category_repo.get_by_id(payload.category_id)
                if not cat:
                    raise EntityNotFoundException(entity_name="Category", entity_id=payload.category_id)
                doc.category_id = payload.category_id
                qdrant_payload["category_id"] = payload.category_id
            else:
                doc.category_id = None
                qdrant_payload["category_id"] = None

        # 2. Update title if explicitly provided in payload
        if "title" in payload.model_fields_set and payload.title is not None:
            clean_title = payload.title.strip()
            if not clean_title:
                raise BadRequestException(message="Tiêu đề tài liệu không được để trống.")
            doc.title = clean_title
            qdrant_payload["title"] = clean_title

        # 3. Save to database
        await self.document_repo.update(doc)

        # 4. Sync Qdrant vector payload
        if qdrant_payload:
            try:
                await self.vector_store.update_payload_by_document_id(
                    document_id=doc.id,
                    payload=qdrant_payload,
                )
            except Exception as e:
                logger.warning(
                    "Failed to sync Qdrant payload for document id=%d: %s",
                    document_id,
                    e,
                )

        # 5. Fetch updated document with category populated
        updated_doc = await self.document_repo.get_with_category(document_id)
        return DocumentResponse.model_validate(updated_doc or doc)
