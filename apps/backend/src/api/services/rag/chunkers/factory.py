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
