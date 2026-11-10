from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Step 1: Extraction & Text Cleaning Preview DTOs
# ---------------------------------------------------------
class PageExtractItem(BaseModel):
    """Cleaned and raw text breakdown for an individual page."""

    page_number: int = Field(..., description="1-based page index")
    raw_text: str = Field(..., description="Raw text as extracted by the parser")
    cleaned_text: str = Field(..., description="Sanitized text after Unicode NFC & noise removal")
    removed_noise: list[str] = Field(default_factory=list, description="List of noise / header lines stripped")
    char_count: int = Field(..., description="Character count of cleaned text")


class ExtractPreviewResponse(BaseModel):
    """Overall document extraction and sanitation preview result."""

    file_name: str = Field(..., description="Original name of the uploaded document")
    total_pages: int = Field(..., description="Total pages parsed")
    total_raw_chars: int = Field(..., description="Character count before cleaning")
    total_cleaned_chars: int = Field(..., description="Character count after cleaning")
    pages: list[PageExtractItem] = Field(default_factory=list, description="Per-page inspection data")


# ---------------------------------------------------------
# Step 2: Chunking Strategy Preview DTOs
# ---------------------------------------------------------
class ChunkPreviewItem(BaseModel):
    """Details for a single generated text chunk."""

    chunk_index: int = Field(..., description="Sequential index of the chunk")
    heading_path: str = Field(default="", description="Hierarchical title path (e.g. Chương I > Điều 2)")
    page_number: int = Field(default=1, description="Source page number")
    token_count: int = Field(..., description="Estimated token count for this chunk")
    content: str = Field(..., description="Enriched chunk content with context prefix")
    overlap_preview: str = Field(default="", description="Leading overlap snippet from previous chunk")


class ChunkPreviewRequest(BaseModel):
    """Payload to test chunking strategy on raw or cleaned text."""

    text: str | None = Field(None, description="Direct text to chunk (if not sending pages)")
    pages: list[dict[str, Any]] | None = Field(None, description="Structured page list from extraction step")
    strategy: str = Field("legal_structural", description="Strategy: 'legal_structural' or 'recursive'")
    chunk_size: int = Field(800, ge=100, le=4000, description="Target chunk size in characters")
    chunk_overlap: int = Field(150, ge=0, le=500, description="Overlap in characters between consecutive chunks")
    document_title: str | None = Field(None, description="Document title for contextual prefixing")


class ChunkPreviewResponse(BaseModel):
    """Overview of chunking execution and token distribution."""

    strategy: str = Field(..., description="Chunking strategy applied")
    total_chunks: int = Field(..., description="Total number of chunks produced")
    avg_tokens: float = Field(..., description="Average tokens per chunk")
    chunks: list[ChunkPreviewItem] = Field(default_factory=list, description="Generated chunks")


# ---------------------------------------------------------
# Step 3: Retrieval & Prompt Assembly Preview DTOs
# ---------------------------------------------------------
class RetrievalPreviewItem(BaseModel):
    """Preview of a single retrieved search chunk with similarity score."""

    rank: int = Field(..., description="Rank in retrieval order (1-based)")
    score: float = Field(..., description="Cosine similarity score (0.0 - 1.0)")
    document_id: int = Field(..., description="Parent document ID")
    title: str = Field(..., description="Document title")
    page_number: int = Field(..., description="Page number")
    chunk_index: int = Field(..., description="Chunk index")
    content_excerpt: str = Field(..., description="Content excerpt of the chunk")


class RetrievalPreviewResponse(BaseModel):
    """Complete retrieval preview including Qdrant matches and final prompt assembly."""

    query: str = Field(..., description="User query evaluated")
    total_found: int = Field(..., description="Number of chunks matching threshold")
    retrieved_chunks: list[RetrievalPreviewItem] = Field(default_factory=list, description="Top ranked chunks")
    assembled_prompt_preview: str = Field(..., description="Final formatted prompt with injected context")
