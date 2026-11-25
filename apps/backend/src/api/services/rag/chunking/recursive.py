"""General-purpose recursive text chunker with sliding overlap."""

from typing import Any

from api.core.config import settings
from api.services.rag.chunking.base import BaseChunker


class RecursiveTextChunker(BaseChunker):
    """General-purpose chunker splitting pages into overlapping segments."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        document_title: str | None = None,
    ):
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))
        self.document_title = document_title.strip() if document_title else None

    def _trailing_overlap(self, chunk_text: str, next_para: str) -> str:
        """Compute word-aligned trailing overlap prefix for the next chunk."""
        if self.chunk_overlap <= 0 or len(chunk_text) <= self.chunk_overlap:
            return next_para
        overlap_text = chunk_text[-self.chunk_overlap :]
        space_idx = overlap_text.find(" ")
        if space_idx != -1:
            overlap_text = overlap_text[space_idx + 1 :]
        return f"{overlap_text}\n\n{next_para}".strip()

    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Chunk a list of parsed pages while maintaining page references and overlap."""
        chunks: list[dict[str, Any]] = []
        context_str = self.document_title or ""

        def append_chunk(text: str, page_number: int) -> None:
            chunks.append(
                self._make_chunk(
                    len(chunks),
                    text,
                    page_start=page_number,
                    page_end=page_number,
                    context=context_str,
                )
            )

        for page_data in pages:
            page_number = int(page_data.get("page_number", 1))
            text = str(page_data.get("cleaned_text") or page_data.get("text") or "")
            paragraphs = self.split_page_text(text)
            if not paragraphs:
                continue

            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()
                    continue

                if current_chunk:
                    append_chunk(current_chunk, page_number)
                    current_chunk = self._trailing_overlap(current_chunk, para)
                else:
                    for part in self.split_oversized_paragraph(
                        para, max_chunk_size=self.chunk_size, overlap=self.chunk_overlap
                    ):
                        append_chunk(part, page_number)

            if current_chunk:
                append_chunk(current_chunk, page_number)

        return chunks
