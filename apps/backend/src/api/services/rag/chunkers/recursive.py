from typing import Any

from api.core.config import settings
from api.services.rag.chunkers.base import BaseChunker


class RecursiveTextChunker(BaseChunker):
    """
    General-purpose document chunker that splits text into overlapping semantic segments
    while preserving page numbers and table integrity.
    """

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    def chunk_pages(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Chunk a list of parsed pages while maintaining page references and overlap."""
        chunks: list[dict[str, Any]] = []
        global_chunk_index = 0

        for page_data in pages:
            page_number = int(page_data.get("page_number", 1))
            text = str(page_data.get("cleaned_text") or page_data.get("text") or "")
            paragraphs = self.split_page_text(text)
            if not paragraphs:
                continue

            current_chunk = ""

            for para in paragraphs:
                if not para:
                    continue
                if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()
                else:
                    if current_chunk:
                        chunks.append({
                            "chunk_index": global_chunk_index,
                            "heading_path": "",
                            "content": current_chunk,
                            "page_number": page_number,
                            "token_count": self.estimate_tokens(current_chunk),
                            "overlap_preview": "",
                        })
                        global_chunk_index += 1

                        if len(current_chunk) > self.chunk_overlap:
                            overlap_text = current_chunk[-self.chunk_overlap :]
                            space_idx = overlap_text.find(" ")
                            if space_idx != -1:
                                overlap_text = overlap_text[space_idx + 1 :]
                            current_chunk = f"{overlap_text}\n\n{para}".strip()
                        else:
                            current_chunk = para
                    else:
                        sub_parts = self.split_oversized_paragraph(
                            para=para,
                            max_chunk_size=self.chunk_size,
                            overlap=self.chunk_overlap,
                        )
                        for part in sub_parts:
                            chunks.append({
                                "chunk_index": global_chunk_index,
                                "heading_path": "",
                                "content": part,
                                "page_number": page_number,
                                "token_count": self.estimate_tokens(part),
                                "overlap_preview": "",
                            })
                            global_chunk_index += 1

            if current_chunk:
                chunks.append({
                    "chunk_index": global_chunk_index,
                    "heading_path": "",
                    "content": current_chunk,
                    "page_number": page_number,
                    "token_count": self.estimate_tokens(current_chunk),
                    "overlap_preview": "",
                })
                global_chunk_index += 1

        return chunks
