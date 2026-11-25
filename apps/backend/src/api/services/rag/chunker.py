"""
HUCE-KMS — Document Chunker Facade (api.services.rag.chunker)

Re-exports chunking strategies from api.services.rag.chunking and exposes
`get_chunker`, `chunk_with_strategy`, and `TextChunker`.
"""

from typing import Any

from api.core.config import settings
from api.services.rag.chunking import (
    BaseChunker,
    LegalStructuralChunker,
    RecursiveTextChunker,
)


def get_chunker(
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> BaseChunker:
    """Instantiate and return the appropriate chunker based on requested strategy."""
    if strategy == "legal_structural":
        return LegalStructuralChunker(document_title=document_title, max_chunk_size=chunk_size)
    return RecursiveTextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_title=document_title,
    )


def chunk_with_strategy(
    pages: list[dict[str, Any]],
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Split text pages using the requested chunking strategy."""
    return get_chunker(
        strategy=strategy,
        document_title=document_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    ).chunk_pages(pages)


class TextChunker(RecursiveTextChunker):
    """Default chunker facade providing strategy-based classmethod entry point."""

    @classmethod
    def chunk_with_strategy(
        cls,
        pages: list[dict[str, Any]],
        strategy: str = "legal_structural",
        document_title: str | None = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> list[dict[str, Any]]:
        """Split pages using requested strategy ('legal_structural' or 'recursive')."""
        return chunk_with_strategy(
            pages=pages,
            strategy=strategy,
            document_title=document_title,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )


__all__ = [
    "BaseChunker",
    "TextChunker",
    "RecursiveTextChunker",
    "LegalStructuralChunker",
    "get_chunker",
    "chunk_with_strategy",
]
