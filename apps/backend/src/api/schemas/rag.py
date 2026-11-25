from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Search query string")
    category_id: UUID | None = Field(default=None, description="Optional category filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to retrieve")
    score_threshold: float | None = Field(
        default=0.4, ge=0.0, le=1.0, description="Minimum cosine similarity score (0.0 to 1.0)"
    )


class SearchResultItem(BaseModel):
    id: str = Field(..., description="UUID point ID in Qdrant")
    document_id: UUID = Field(..., description="Parent document identifier")
    title: str = Field(..., description="Document title")
    category_id: UUID | None = Field(default=None, description="Category identifier")
    page_number: int = Field(..., description="Page number where the chunk starts")
    page_start: int | None = Field(default=None, description="Starting page number")
    page_end: int | None = Field(default=None, description="Ending page number")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    score: float = Field(..., description="Cosine similarity score")
    context: str | None = Field(default=None, description="Hierarchical breadcrumb context")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured chunk metadata")
    content: str = Field(..., description="Clean text content of the chunk")


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int


class CitationSource(BaseModel):
    document_id: UUID
    title: str
    page_number: int
    page_start: int | None = None
    page_end: int | None = None
    chunk_index: int
    score: float
    context: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    snippet: str


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="User question or inquiry")
    category_id: UUID | None = Field(default=None, description="Optional category filter")
    top_k: int = Field(default=5, ge=1, le=15, description="Number of context chunks to retrieve")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0, description="LLM sampling temperature")


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[CitationSource]
    total_sources: int
