from pathlib import Path as FilePath
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status

from api.core.dependencies import AdminUserDep, CurrentUserDep, DatabaseDep, PaginationDep
from api.repositories.category import CategoryRepository
from api.repositories.document import DocumentRepository
from api.repositories.document_chunk import DocumentChunkRepository
from api.schemas.common import BaseResponse, PaginatedData, PaginationMeta
from api.schemas.document import DocumentDetailResponse, DocumentResponse
from api.services.document import DocumentService
from api.services.rag.embedder import GeminiEmbeddingService
from api.services.rag.vector_store import QdrantVectorStore

router = APIRouter()


def get_document_service(db: DatabaseDep) -> DocumentService:
    document_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)
    category_repo = CategoryRepository(db)
    embedder = GeminiEmbeddingService()
    vector_store = QdrantVectorStore()
    return DocumentService(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        category_repo=category_repo,
        embedder=embedder,
        vector_store=vector_store,
    )


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@router.post(
    "/upload",
    response_model=BaseResponse[DocumentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document into RAG pipeline (PDF, TXT, MD)",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file (.pdf, .txt, .md)"),
    title: str | None = Form(None, description="Document display title (defaults to filename)"),
    category_id: int | None = Form(None, description="Category identifier"),
    current_user: CurrentUserDep = None,
    service: DocumentServiceDep = None,
):
    file_bytes = await file.read()
    file_name = file.filename or "unknown_document.pdf"
    doc_title = title.strip() if title and title.strip() else FilePath(file_name).stem

    document = await service.upload_and_process_document(
        file_bytes=file_bytes,
        file_name=file_name,
        title=doc_title,
        category_id=category_id,
        uploader_id=current_user.id if current_user else None,
    )

    return BaseResponse(
        code="DOCUMENT_INDEXED",
        message="Document uploaded, parsed, and vector indexed successfully.",
        data=document,
    )


@router.get(
    "/",
    response_model=BaseResponse[PaginatedData[DocumentResponse]],
    status_code=status.HTTP_200_OK,
    summary="List documents with pagination and filters",
)
async def list_documents(
    pagination: PaginationDep,
    service: DocumentServiceDep,
    category_id: int | None = Query(None, description="Filter by category ID"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status (pending, processing, indexed, failed)"),
    q: str | None = Query(None, description="Search keyword in title or filename"),
):
    items, total = await service.list_documents(
        skip=pagination.skip,
        limit=pagination.limit,
        category_id=category_id,
        status=status_filter,
        query=q,
    )

    return BaseResponse(
        message="Documents retrieved successfully.",
        data=PaginatedData(
            items=list(items),
            pagination=PaginationMeta.create(
                total=total,
                skip=pagination.skip,
                limit=pagination.limit,
            ),
        ),
    )


@router.get(
    "/{document_id}",
    response_model=BaseResponse[DocumentDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get document details including text chunks",
)
async def get_document(
    document_id: Annotated[int, Path(ge=1, description="Document unique identifier")],
    service: DocumentServiceDep,
):
    document = await service.get_document_detail(document_id)
    return BaseResponse(
        message="Document details retrieved successfully.",
        data=document,
    )


@router.delete(
    "/{document_id}",
    response_model=BaseResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete a document, its chunks, vector embeddings, and physical file (Admin only)",
)
async def delete_document(
    document_id: Annotated[int, Path(ge=1, description="Document unique identifier")],
    admin_user: AdminUserDep,
    service: DocumentServiceDep,
):
    await service.delete_document(document_id)
    return BaseResponse(
        message="Document and all associated vector embeddings deleted successfully.",
        data=None,
    )
