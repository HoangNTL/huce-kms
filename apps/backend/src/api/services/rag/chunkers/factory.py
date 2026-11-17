from typing import Any

from api.core.config import settings
from api.services.rag.chunkers.base import BaseChunker
from api.services.rag.chunkers.legal import LegalStructuralChunker
from api.services.rag.chunkers.recursive import RecursiveTextChunker


def get_chunker(
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> BaseChunker:
    """Instantiate and return the appropriate chunker based on requested strategy."""
    if strategy == "legal_structural":
        return LegalStructuralChunker(
            document_title=document_title,
            max_chunk_size=chunk_size,
        )
    return RecursiveTextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def chunk_with_strategy(
    pages: list[dict[str, Any]],
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Factory helper to split text pages using the requested chunking strategy."""
    chunker = get_chunker(
        strategy=strategy,
        document_title=document_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return chunker.chunk_pages(pages)


def generate_chunk_preview(
    text: str | None = None,
    pages: list[dict[str, Any]] | None = None,
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> Any:
    """Process text/pages and return structured chunking preview with token analytics."""
    from api.core.exceptions import BadRequestException
    from api.schemas.rag_preview import ChunkPreviewItem, ChunkPreviewResponse

    if pages:
        input_pages = pages
    elif text and text.strip():
        input_pages = [{"page_number": 1, "text": text.strip()}]
    else:
        raise BadRequestException(message="Either 'text' or 'pages' must be provided for chunk preview.")

    raw_chunks = chunk_with_strategy(
        pages=input_pages,
        strategy=strategy,
        document_title=document_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunk_items = [
        ChunkPreviewItem(
            chunk_index=c["chunk_index"],
            heading_path=c.get("heading_path", ""),
            page_number=c.get("page_number", 1),
            token_count=c.get("token_count", 0),
            content=c.get("content", ""),
            overlap_preview=c.get("overlap_preview", ""),
        )
        for c in raw_chunks
    ]

    total_tokens = sum(c.token_count for c in chunk_items)
    avg_tokens = round(total_tokens / len(chunk_items), 1) if chunk_items else 0.0

    return ChunkPreviewResponse(
        strategy=strategy,
        total_chunks=len(chunk_items),
        avg_tokens=avg_tokens,
        chunks=chunk_items,
    )
