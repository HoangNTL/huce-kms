import re
from typing import Any

from api.core.config import settings


class TextChunker:
    """Splits document text into overlapping semantic chunks with page tracking."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for Vietnamese/English mixed text."""
        # Simple heuristic: average ~1.3 tokens per whitespace-separated word
        words = text.split()
        return max(1, int(len(words) * 1.3))

    def split_page_text(self, text: str) -> list[str]:
        """Split page text into smaller paragraphs or segments."""
        # Clean multiple spaces and redundant newlines
        cleaned = re.sub(r"\r\n|\r", "\n", text)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        return paragraphs if paragraphs else [cleaned.strip()]

    def chunk_pages(
        self, pages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Chunk a list of parsed pages while maintaining page references and overlap."""
        chunks: list[dict[str, Any]] = []
        global_chunk_index = 0

        for page_data in pages:
            page_number = int(page_data["page_number"])
            text = str(page_data["text"])
            paragraphs = self.split_page_text(text)

            current_chunk = ""

            for para in paragraphs:
                if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                    current_chunk = f"{current_chunk}\n\n{para}".strip()
                else:
                    # Current chunk is full, emit it if not empty
                    if current_chunk:
                        chunks.append({
                            "chunk_index": global_chunk_index,
                            "content": current_chunk,
                            "page_number": page_number,
                            "token_count": self.estimate_tokens(current_chunk),
                        })
                        global_chunk_index += 1

                        # Carry over overlap
                        if len(current_chunk) > self.chunk_overlap:
                            overlap_text = current_chunk[-self.chunk_overlap :]
                            # Avoid cutting in the middle of a word
                            space_idx = overlap_text.find(" ")
                            if space_idx != -1:
                                overlap_text = overlap_text[space_idx + 1 :]
                            current_chunk = f"{overlap_text}\n\n{para}".strip()
                        else:
                            current_chunk = para
                    else:
                        # Paragraph itself exceeds chunk_size, split by characters
                        start = 0
                        while start < len(para):
                            end = start + self.chunk_size
                            part = para[start:end].strip()
                            if part:
                                chunks.append({
                                    "chunk_index": global_chunk_index,
                                    "content": part,
                                    "page_number": page_number,
                                    "token_count": self.estimate_tokens(part),
                                })
                                global_chunk_index += 1
                            start += max(1, self.chunk_size - self.chunk_overlap)

            # Emit final pending chunk of the page
            if current_chunk:
                chunks.append({
                    "chunk_index": global_chunk_index,
                    "content": current_chunk,
                    "page_number": page_number,
                    "token_count": self.estimate_tokens(current_chunk),
                })
                global_chunk_index += 1

        return chunks
