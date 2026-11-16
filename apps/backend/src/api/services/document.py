import hashlib
import logging
import uuid
from collections.abc import Sequence
from pathlib import Path

from api.core.config import settings
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
    DocumentResponse,
    DocumentUpdate,
)
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.rag.chunker import TextChunker
from api.services.rag.cleaner import TextCleaner
from api.services.rag.embedder import GeminiEmbeddingService
from api.services.rag.parser import DocumentParser
from api.services.rag.vector_store import QdrantVectorStore

logger = logging.getLogger("huce_kms.services.document")


class DocumentService:
    """Business logic service for document lifecycle management and RAG ingestion pipeline."""

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: DocumentChunkRepository,
        category_repo: CategoryRepository,
        embedder: EmbeddingManager | GeminiEmbeddingService,
        vector_store: QdrantVectorStore,
    ):
        self.document_repo = document_repo
        self.chunk_repo = chunk_repo
        self.category_repo = category_repo
        self.embedder = embedder
        self.vector_store = vector_store
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
        category_id: int | None = None,
        uploader_id: int | None = None,
        chunk_strategy: str = "legal_structural",
    ) -> DocumentResponse:
        """Validate, store, parse, embed and index an uploaded document into PostgreSQL and Qdrant."""
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

        # 5. Save physical file to disk (sanitize filename to prevent directory traversal)
        clean_file_name = Path(file_name).name or "document"
        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        unique_file_name = f"{uuid.uuid4().hex[:12]}_{clean_file_name}"
        saved_file_path = settings.UPLOAD_DIR / unique_file_name
        saved_file_path.write_bytes(file_bytes)

        # 6. Create preliminary Document record in PostgreSQL (status = 'pending')
        document = Document(
            title=title.strip(),
            file_name=clean_file_name,
            file_path=str(saved_file_path),
            file_size=len(file_bytes),
            file_type=suffix.lstrip("."),
            file_hash=file_hash,
            status="pending",
            category_id=category_id,
            uploader_id=uploader_id,
            total_pages=0,
            chunk_count=0,
            error_message=None,
        )
        document = await self.document_repo.create(document)

        # 7. Execute Ingestion Pipeline (Parsing -> Chunking -> Embedding -> Qdrant + DB Indexing)
        try:
            document.status = "processing"
            await self.document_repo.update(document)

            # Step 7a: Parse raw text pages
            raw_pages = self.parser.parse(file_bytes, file_name)
            total_pages = len(raw_pages)

            # Step 7b: Clean and normalize text (Unicode NFC, noise & pagination removal)
            cleaned_pages = TextCleaner.clean_pages(raw_pages)

            # Step 7c: Chunk using structural legal strategy or configured strategy
            raw_chunks = TextChunker.chunk_with_strategy(
                pages=cleaned_pages,
                strategy=chunk_strategy,
                document_title=document.title,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            if not raw_chunks:
                raise BadRequestException(
                    message="No extractable text content found in document."
                )

            # Assign UUID to each chunk (for 1-1 mapping with Qdrant Point IDs)
            chunks_with_id = []
            for c in raw_chunks:
                chunk_dict = dict(c)
                chunk_dict["id"] = str(uuid.uuid4())
                chunk_dict["document_id"] = document.id
                chunk_dict["title"] = document.title
                chunk_dict["category_id"] = document.category_id
                chunks_with_id.append(chunk_dict)

            # Step 7c: Generate vector embeddings via Gemini
            texts_to_embed = [c["content"] for c in chunks_with_id]
            embeddings = await self.embedder.generate_embeddings_batch(texts_to_embed)

            # Step 7d: Index points to Qdrant Vector Store
            await self.vector_store.upsert_chunks(chunks_with_id, embeddings)

            # Step 7e: Persist chunks to PostgreSQL
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

            # Step 7f: Mark document as successfully indexed
            document.status = "indexed"
            document.total_pages = total_pages
            document.chunk_count = len(chunks_with_id)
            document.error_message = None
            document = await self.document_repo.update(document)

            logger.info(
                "Document id=%d ('%s') successfully indexed with %d chunks and %d pages.",
                document.id,
                document.title,
                document.chunk_count,
                document.total_pages,
            )

        except Exception as e:
            logger.error("Failed to process document id=%d: %s", document.id, e)
            # Remove physical file to avoid orphaned disk storage on transaction rollback
            try:
                saved_file_path.unlink(missing_ok=True)
            except Exception as cleanup_err:
                logger.warning("Could not delete physical file '%s': %s", saved_file_path, cleanup_err)

            # Best-effort deletion of partial vector embeddings from Qdrant
            try:
                await self.vector_store.delete_by_document_id(document.id)
            except Exception as qdrant_err:
                logger.warning("Could not delete vector points for document id=%d: %s", document.id, qdrant_err)

            document.status = "failed"
            document.error_message = str(e)
            await self.document_repo.update(document)
            raise

        refreshed = await self.document_repo.get_with_category(document.id)
        return DocumentResponse.model_validate(refreshed or document)

    async def get_document_by_id(self, document_id: int) -> DocumentResponse:
        """Retrieve a document by ID."""
        doc = await self.document_repo.get_with_category(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        return DocumentResponse.model_validate(doc)

    async def get_document_detail(self, document_id: int) -> DocumentDetailResponse:
        """Retrieve document metadata and all associated text chunks."""
        doc = await self.document_repo.get_with_chunks(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)
        return DocumentDetailResponse.model_validate(doc)

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 10,
        category_id: int | None = None,
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

    async def delete_document(self, document_id: int) -> None:
        """Delete document, cascading its chunks, vector embeddings in Qdrant, and physical file."""
        doc = await self.document_repo.get_by_id(document_id)
        if not doc:
            raise EntityNotFoundException(entity_name="Document", entity_id=document_id)

        # 1. Delete points in Qdrant Vector DB
        try:
            await self.vector_store.delete_by_document_id(document_id)
        except Exception as e:
            logger.warning("Failed to delete Qdrant points for document id=%d: %s", document_id, e)

        # 2. Delete physical file from disk
        try:
            file_path = Path(doc.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning("Failed to remove file '%s' from disk: %s", doc.file_path, e)

        # 3. Delete Document record from PostgreSQL (cascades chunks automatically)
        await self.document_repo.delete(doc)
        logger.info("Deleted document id=%d ('%s')", document_id, doc.title)

    async def update_document(
        self, document_id: int, payload: DocumentUpdate
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
