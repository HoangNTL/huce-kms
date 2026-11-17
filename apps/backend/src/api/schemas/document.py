from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from api.schemas.category import CategoryResponse

DocumentStatus = Literal["uploaded", "pending", "processing", "indexed", "failed"]


class DocumentChunkResponse(BaseModel):
    id: UUID = Field(..., description="UUID point ID matching Qdrant Point ID")
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int
    token_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, examples=["Academic Regulations 2026"])
    category_id: UUID | None = Field(default=None, description="Target category identifier")


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    category_id: UUID | None = Field(default=None)


class DocumentResponse(DocumentBase):
    id: UUID
    file_name: str
    file_path: str
    file_size: int
    file_type: str
    file_hash: str
    status: DocumentStatus
    created_by_id: UUID | None = Field(default=None, description="User who uploaded/created document")
    total_pages: int
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = Field(default=None, description="Soft-delete timestamp if deleted")
    category: CategoryResponse | None = None
    download_url: str | None = Field(default=None, description="Presigned download or view URL for the original document")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def uploader_id(self) -> UUID | None:
        """Backward-compatibility accessor for uploader_id."""
        return self.created_by_id

    @field_validator("download_url", mode="before")
    @classmethod
    def filter_download_url(cls, v: Any) -> str | None:
        if isinstance(v, str):
            return v
        if v is None:
            return None
        # In unit tests with MagicMock models, attribute access produces a MagicMock
        if hasattr(v, "_mock_name") or type(v).__name__ in ("MagicMock", "AsyncMock"):
            return None
        return str(v)

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower().strip()
        return v


class DocumentDetailResponse(DocumentResponse):
    chunks: list[DocumentChunkResponse] = Field(default_factory=list)


class DocumentDownloadUrlResponse(BaseModel):
    document_id: UUID
    file_name: str
    download_url: str
    expires_in_seconds: int = 3600


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    message: str = Field(default="Document uploaded and queued for processing.")
