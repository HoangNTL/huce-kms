"""
HUCE-KMS — Document Chunker Service Facade (api.services.rag.chunker)

Backward-compatible facade delegating to modular chunkers in api.services.rag.chunkers:
  - RecursiveTextChunker: for general, unformatted text and markdown tables.
  - LegalStructuralChunker: for Vietnamese administrative decrees/regulations (Chương/Mục/Điều/Khoản).
"""

from typing import Any

from api.core.config import settings
from api.services.rag.chunkers.base import BaseChunker
from api.services.rag.chunkers.factory import (
    chunk_with_strategy,
    generate_chunk_preview,
    get_chunker,
)
from api.services.rag.chunkers.legal import LegalStructuralChunker
from api.services.rag.chunkers.recursive import RecursiveTextChunker


class TextChunker(RecursiveTextChunker):
    """
    Backward-compatible facade around RecursiveTextChunker.
    Retains factory classmethods chunk_with_strategy and generate_chunk_preview.
    """

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

    @classmethod
    def generate_chunk_preview(
        cls,
        text: str | None = None,
        pages: list[dict[str, Any]] | None = None,
        strategy: str = "legal_structural",
        document_title: str | None = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> Any:
        """Process text/pages and return structured chunking preview."""
        return generate_chunk_preview(
            text=text,
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
    "generate_chunk_preview",
]
