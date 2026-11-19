from pathlib import Path
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

from api.services.crawler.schemas import PageMetadata


class IngestPagePayload(BaseModel):
    """Payload representing read artifacts of a single crawled page."""

    page_dir: Path
    metadata: PageMetadata
    markdown_content: str
    pdf_files: list[Path] = Field(default_factory=list)
    image_files: list[Path] = Field(default_factory=list)


class IngestItemResult(BaseModel):
    """Result of ingesting a single document item (Markdown page or attached PDF)."""

    document_id: UUID | None = None
    title: str
    file_name: str
    file_type: str
    source_url: str
    status: Literal["uploaded", "indexed", "skipped", "failed"]
    chunks_count: int = 0
    error: str | None = None


class IngestSummaryResponse(BaseModel):
    """Aggregate summary of an ingestion run."""

    total_pages: int
    total_documents: int
    successful: int
    skipped: int
    failed: int
    items: list[IngestItemResult] = Field(default_factory=list)

    @property
    def total_succeeded(self) -> int:
        return self.successful

    @property
    def total_failed(self) -> int:
        return self.failed
