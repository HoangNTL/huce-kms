from pathlib import Path as FilePath
from typing import Annotated
from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile, status
from fastapi.responses import RedirectResponse

from api.core.dependencies import AdminUserDep, CurrentUserDep, DatabaseDep, PaginationDep
from api.core.exceptions import EntityNotFoundException
from api.repositories.category import CategoryRepository
from api.repositories.document import DocumentRepository
from api.repositories.document_chunk import DocumentChunkRepository
from api.schemas.common import BaseResponse, PaginatedData, PaginationMeta
from api.schemas.document import (
    DocumentDetailResponse,
    DocumentDownloadUrlResponse,
    DocumentResponse,
    DocumentUpdate,
)
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.document import DocumentService
from api.services.rag.vector_store import QdrantVectorStore
from api.services.storage import StorageService, get_storage_service
from api.v1.routes.rag import get_embedding_manager

router = APIRouter()


def get_document_service(
    db: DatabaseDep,
    embedder: Annotated[EmbeddingManager, Depends(get_embedding_manager)],
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
) -> DocumentService:
    document_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)
    category_repo = CategoryRepository(db)
    vector_store = QdrantVectorStore()
    return DocumentService(
        document_repo=document_repo,
        chunk_repo=chunk_repo,
        category_repo=category_repo,
        embedder=embedder,
        vector_store=vector_store,
        storage_service=storage_service,
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
    chunk_strategy: str = Form("legal_structural", description="Chunking strategy: 'legal_structural' or 'recursive'"),
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
        chunk_strategy=chunk_strategy,
    )

    return BaseResponse(
        code="DOCUMENT_INDEXED",
        message="Document uploaded, parsed, and vector indexed successfully.",
        data=document,
    )


@router.get(
    "",
    response_model=BaseResponse[PaginatedData[DocumentResponse]],
    include_in_schema=False,
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
    status_filter: str | None = Query(None, alias="status", description="Filter by status (uploaded, pending, processing, indexed, failed)"),
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
    "/raw/{object_key:path}",
    summary="Directly serve raw document file from storage",
)
async def get_raw_document_file(
    object_key: str,
    storage_service: Annotated[StorageService, Depends(get_storage_service)],
):
    try:
        file_bytes = await storage_service.get_file(object_key)
    except FileNotFoundError:
        raise EntityNotFoundException(entity_name="File", entity_id=object_key)

    filename = FilePath(object_key).name
    suffix = FilePath(object_key).suffix.lower()
    content_type_map = {
        ".pdf": "application/pdf",
        ".txt": "text/plain; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
    }
    content_type = content_type_map.get(suffix, "application/octet-stream")
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
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


@router.patch(
    "/{document_id}",
    response_model=BaseResponse[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="Update document title or category metadata (Admin only)",
)
async def update_document(
    document_id: Annotated[int, Path(ge=1, description="Document unique identifier")],
    payload: DocumentUpdate,
    admin_user: AdminUserDep,
    service: DocumentServiceDep,
):
    updated = await service.update_document(document_id, payload)
    return BaseResponse(
        message="Document updated successfully.",
        data=updated,
    )


@router.get(
    "/{document_id}/download-url",
    response_model=BaseResponse[DocumentDownloadUrlResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate a presigned URL to download or view the original file",
)
async def get_document_download_url(
    document_id: Annotated[int, Path(ge=1, description="Document unique identifier")],
    service: DocumentServiceDep,
    expiry_seconds: int = Query(3600, ge=60, le=86400, description="URL validity in seconds"),
):
    result = await service.get_document_download_url(document_id, expiry_seconds=expiry_seconds)
    return BaseResponse(
        message="Presigned download URL generated successfully.",
        data=result,
    )


@router.get(
    "/{document_id}/download",
    summary="Directly download original document file",
)
async def download_document(
    document_id: Annotated[int, Path(ge=1, description="Document unique identifier")],
    service: DocumentServiceDep,
):
    url_info = await service.get_document_download_url(document_id)
    if url_info.download_url.startswith("http"):
        return RedirectResponse(
            url=url_info.download_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    file_bytes, file_name, content_type = await service.get_document_file_bytes(document_id)
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
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
