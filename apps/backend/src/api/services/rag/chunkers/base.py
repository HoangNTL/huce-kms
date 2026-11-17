import re
from abc import ABC, abstractmethod
from typing import Any


class BaseChunker(ABC):
    """Abstract base class for document chunkers with common token & formatting utilities."""

    @abstractmethod
    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split a list of parsed pages into semantic chunks."""
        pass

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for Vietnamese and English mixed text."""
        # Simple heuristic: average ~1.3 tokens per whitespace-separated word
        words = text.split()
        return max(1, int(len(words) * 1.3))

    @staticmethod
    def split_page_text(text: str) -> list[str]:
        """Split raw page text into normalized paragraphs."""
        if not text or not text.strip():
            return []
        cleaned = re.sub(r"\r\n|\r", "\n", text)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return [p.strip() for p in cleaned.split("\n\n") if p.strip()]

    @classmethod
    def is_markdown_table(cls, text: str) -> bool:
        """Check whether a text block represents a valid Markdown table."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if len(lines) >= 2:
            first_is_row = lines[0].startswith("|") and lines[0].endswith("|")
            second_is_sep = "---" in lines[1] and lines[1].startswith("|")
            return first_is_row and second_is_sep
        return False

    @classmethod
    def split_markdown_table(cls, table_text: str, max_chunk_size: int) -> list[str]:
        """
        Split an oversized Markdown table along row boundaries without breaking cells,
        repeating the table header rows (header + separator) on every generated chunk.
        """
        lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
        if len(lines) <= 2:
            return [table_text]

        header_lines = lines[:2]
        header_str = "\n".join(header_lines)
        header_len = len(header_str)

        data_rows = lines[2:]
        chunks: list[str] = []
        current_rows: list[str] = []
        current_len = header_len

        for row in data_rows:
            row_len = len(row) + 1  # include newline
            if current_rows and (current_len + row_len > max_chunk_size):
                chunks.append(f"{header_str}\n" + "\n".join(current_rows))
                current_rows = [row]
                current_len = header_len + row_len
            else:
                current_rows.append(row)
                current_len += row_len

        if current_rows:
            chunks.append(f"{header_str}\n" + "\n".join(current_rows))

        return chunks

    @classmethod
    def split_oversized_paragraph(
        cls, para: str, max_chunk_size: int, overlap: int = 0
    ) -> list[str]:
        """
        Split a paragraph that exceeds max_chunk_size along sentence or word boundaries.
        If the block is a Markdown table, delegating to split_markdown_table.
        """
        if cls.is_markdown_table(para):
            return cls.split_markdown_table(para, max_chunk_size)

        parts: list[str] = []
        remaining = para
        while remaining:
            if len(remaining) <= max_chunk_size:
                parts.append(remaining.strip())
                break

            # Find best split boundary within window [max_chunk_size - 150, max_chunk_size]
            search_window_start = max(1, max_chunk_size - 150)
            cut_idx = max_chunk_size
            for sep in [". ", ".\n", "? ", "! ", "; ", ", ", " ", "\n"]:
                pos = remaining.rfind(sep, search_window_start, max_chunk_size)
                if pos != -1:
                    cut_idx = pos + len(sep)
                    break

            part = remaining[:cut_idx].strip()
            if part:
                parts.append(part)

            if overlap > 0 and len(part) > overlap:
                step_back = max(0, cut_idx - overlap)
                remaining = remaining[step_back:].strip()
            else:
                remaining = remaining[cut_idx:].strip()

        return parts
