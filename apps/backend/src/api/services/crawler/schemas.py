from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, Field


class CrawledMediaItem(BaseModel):
    """Metadata for a downloaded PDF or image attachment."""

    url: str
    local_path: str
    file_name: str
    file_size: int
    file_hash: str
    mime_type: str
    media_type: Literal["pdf", "image"]
    status: Literal["success", "failed", "skipped"] = "success"
    error: str | None = None


class PageSourceMeta(BaseModel):
    """Source URL and domain information."""

    url: str
    canonical_url: str
    domain: str
    type: str = "web"


class PageContentMeta(BaseModel):
    """Main article content information."""

    title: str
    published_at: str | None = None
    crawled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    markdown_file: str = "content.md"
    content_hash: str


class PageMediaMeta(BaseModel):
    """Collections of discovered & downloaded media."""

    pdfs: list[CrawledMediaItem] = Field(default_factory=list)
    images: list[CrawledMediaItem] = Field(default_factory=list)


class PageCrawlStatus(BaseModel):
    """Execution status and HTTP code."""

    status: Literal["success", "failed", "partial"] = "success"
    http_status: int = 200
    error_message: str | None = None


class PageMetadata(BaseModel):
    """Full metadata manifest matching Section 5 of the architecture spec."""

    schema_version: str = "1.0"
    source: PageSourceMeta
    content: PageContentMeta
    media: PageMediaMeta = Field(default_factory=PageMediaMeta)
    crawl: PageCrawlStatus = Field(default_factory=PageCrawlStatus)

    def __init__(
        self,
        source_url: str | None = None,
        canonical_url: str | None = None,
        domain: str | None = None,
        title: str | None = None,
        published_at: str | None = None,
        crawled_at: str | None = None,
        content_hash: str | None = None,
        markdown_file: str = "content.md",
        **data: Any,
    ):
        if source_url and "source" not in data:
            data["source"] = PageSourceMeta(
                url=source_url,
                canonical_url=canonical_url or source_url,
                domain=domain or "",
            )
        if title and content_hash and "content" not in data:
            data["content"] = PageContentMeta(
                title=title,
                published_at=published_at,
                crawled_at=crawled_at or datetime.now(timezone.utc).isoformat(),
                markdown_file=markdown_file,
                content_hash=content_hash,
            )
        super().__init__(**data)


class CrawlResult(BaseModel):
    """High-level summary of a crawled page run."""

    url: str
    status: Literal["success", "failed", "partial"]
    title: str
    artifact_dir: Path
    markdown_path: Path | None = None
    metadata_path: Path | None = None
    pdf_count: int = 0
    image_count: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = Field(default_factory=list)
