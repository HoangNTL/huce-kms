from uuid import UUID
from pydantic import BaseModel, Field


class CrawlDirectRequest(BaseModel):
    url: str = Field(..., description="Target article or document URL to crawl")
    auto_ingest: bool = Field(default=False, description="Whether to automatically ingest to RAG after crawl")
    auto_publish: bool = Field(default=False, description="If auto-ingest is True, whether to index vectors immediately")
    category_id: UUID | None = Field(default=None, description="Optional category ID for ingested documents")


class DiscoverRequest(BaseModel):
    url: str = Field(..., description="Category listing page, sitemap or RSS feed URL")
    max_items: int = Field(default=50, ge=1, le=200, description="Maximum candidate links to discover")


class ApproveQueueRequest(BaseModel):
    queue_file: str | None = Field(default=None, description="Discovered queue file name (defaults to latest)")
    approved_urls: list[str] | None = Field(default=None, description="List of specific URLs to approve")
    approve_all: bool = Field(default=False, description="Approve all discovered URLs in the file")


class IngestSessionRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Session ID to ingest")
    page_hash: str | None = Field(default=None, description="Specific page hash to ingest")
    category_id: UUID | None = Field(default=None, description="Category ID to assign")
    auto_publish: bool = Field(default=False, description="Index vectors into Qdrant immediately")
