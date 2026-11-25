"""
HUCE-KMS — Document Chunker Service (api.services.rag.chunker)

Provides document chunking strategies:
  - RecursiveTextChunker (and TextChunker facade): general text and markdown tables.
  - LegalStructuralChunker: Vietnamese administrative regulations (Chương/Mục/Điều/Khoản).
"""

from abc import ABC, abstractmethod
import re
from typing import Any

from api.core.config import settings


class BaseChunker(ABC):
    """Abstract base class for document chunkers with common token and splitting utilities."""

    @abstractmethod
    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split a list of parsed pages into semantic chunks."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for Vietnamese and English mixed text (~1.3 tokens/word)."""
        return max(1, int(len(text.split()) * 1.3))

    @classmethod
    def _make_chunk(
        cls,
        chunk_index: int,
        content: str,
        page_number: int,
        heading_path: str = "",
    ) -> dict[str, Any]:
        """Build a standardized chunk payload dictionary."""
        return {
            "chunk_index": chunk_index,
            "heading_path": heading_path,
            "content": content,
            "page_number": page_number,
            "token_count": cls.estimate_tokens(content),
        }

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
        lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return False
        first_is_row = lines[0].startswith("|") and lines[0].endswith("|")
        second_is_sep = "---" in lines[1] and lines[1].startswith("|")
        return first_is_row and second_is_sep

    @classmethod
    def split_markdown_table(cls, table_text: str, max_chunk_size: int) -> list[str]:
        """Split an oversized Markdown table along row boundaries, repeating the header rows."""
        lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
        if len(lines) <= 2:
            return [table_text]

        header_str = "\n".join(lines[:2])
        header_len = len(header_str)
        chunks: list[str] = []
        current_rows: list[str] = []
        current_len = header_len

        for row in lines[2:]:
            row_len = len(row) + 1
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
        """Split an oversized paragraph along sentence/word boundaries (or table rows)."""
        if cls.is_markdown_table(para):
            return cls.split_markdown_table(para, max_chunk_size)

        parts: list[str] = []
        remaining = para
        while remaining:
            if len(remaining) <= max_chunk_size:
                parts.append(remaining.strip())
                break

            search_start = max(1, max_chunk_size - 150)
            cut_idx = max_chunk_size
            for sep in [". ", ".\n", "? ", "! ", "; ", ", ", " ", "\n"]:
                pos = remaining.rfind(sep, search_start, max_chunk_size)
                if pos != -1:
                    cut_idx = pos + len(sep)
                    break

            part = remaining[:cut_idx].strip()
            if part:
                parts.append(part)

            step_back = max(0, cut_idx - overlap) if (overlap > 0 and len(part) > overlap) else cut_idx
            remaining = remaining[step_back:].strip()

        return parts


class RecursiveTextChunker(BaseChunker):
    """General-purpose chunker splitting pages into overlapping segments."""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = max(50, chunk_size)
        self.chunk_overlap = max(0, min(chunk_overlap, self.chunk_size - 1))

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
                    chunks.append(self._make_chunk(len(chunks), current_chunk, page_number))
                    current_chunk = self._trailing_overlap(current_chunk, para)
                else:
                    sub_parts = self.split_oversized_paragraph(
                        para=para,
                        max_chunk_size=self.chunk_size,
                        overlap=self.chunk_overlap,
                    )
                    for part in sub_parts:
                        chunks.append(self._make_chunk(len(chunks), part, page_number))

            if current_chunk:
                chunks.append(self._make_chunk(len(chunks), current_chunk, page_number))

        return chunks


class LegalStructuralChunker(BaseChunker):
    """Structure-aware chunker for Vietnamese regulations (Chương -> Mục -> Điều -> Khoản)."""

    CHAPTER_PATTERN = re.compile(r"^(?:CHƯƠNG|Chương)\s+([IVXLCDM\d]+)(?:\s*[:\.\-]\s*(.*))?$", re.MULTILINE)
    SECTION_PATTERN = re.compile(r"^(?:MỤC|Mục)\s+(\d+)(?:\s*[:\.\-]\s*(.*))?$", re.MULTILINE)
    ARTICLE_PATTERN = re.compile(r"^(?:ĐIỀU|Điều)\s+(\d+)(?:\s*[:\.\-]\s*(.*))?$", re.MULTILINE)

    def __init__(
        self,
        document_title: str | None = None,
        max_chunk_size: int = 1200,
    ):
        self.document_title = document_title.strip() if document_title else None
        self.max_chunk_size = max(200, max_chunk_size)

    def _has_legal_structure(self, pages: list[dict[str, Any]]) -> bool:
        """Check if pages contain any Article or Chapter patterns."""
        for page in pages:
            text = str(page.get("cleaned_text") or page.get("text") or "")
            if self.ARTICLE_PATTERN.search(text) or self.CHAPTER_PATTERN.search(text):
                return True
        return False

    def _is_heading_line(self, line: str) -> bool:
        return bool(
            self.CHAPTER_PATTERN.match(line)
            or self.SECTION_PATTERN.match(line)
            or self.ARTICLE_PATTERN.match(line)
        )

    def _read_heading_with_lookahead(
        self, lines: list[str], next_idx: int, match: re.Match[str], label: str
    ) -> tuple[str, int]:
        """Extract heading label + title, consuming the next line if the title wraps."""
        num = match.group(1)
        title = (match.group(2) or "").strip(": .-")
        if not title and next_idx < len(lines):
            candidate = lines[next_idx].strip()
            if candidate and not self._is_heading_line(candidate):
                title = candidate
                next_idx += 1
        heading = f"{label} {num}" + (f": {title}" if title else "")
        return heading, next_idx

    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Chunk pages hierarchically by regulation articles with contextual breadcrumbs."""
        if not self._has_legal_structure(pages):
            return RecursiveTextChunker(chunk_size=self.max_chunk_size).chunk_pages(pages)

        chunks: list[dict[str, Any]] = []
        current_chapter = ""
        current_section = ""
        current_article = ""
        article_page = 1
        article_lines: list[str] = []

        def emit_chunk(body: str, prefix: str, heading_path: str) -> None:
            enriched = f"{prefix}{body}".strip()
            chunks.append(self._make_chunk(len(chunks), enriched, article_page, heading_path))

        def flush_article_chunk() -> None:
            nonlocal article_lines
            if not article_lines:
                return
            body_text = "\n".join(article_lines).strip()
            article_lines = []
            if not body_text:
                return

            path_parts = [p for p in (current_chapter, current_section, current_article) if p]
            heading_path = " > ".join(path_parts) if path_parts else (self.document_title or "")

            prefix_parts = []
            if self.document_title:
                prefix_parts.append(f"[Tài liệu: {self.document_title}]")
            if heading_path:
                prefix_parts.append(f"[{heading_path}]")
            prefix = " ".join(prefix_parts) + "\n" if prefix_parts else ""

            if len(body_text) <= self.max_chunk_size:
                emit_chunk(body_text, prefix, heading_path)
                return

            paragraphs = [
                p.strip()
                for p in re.split(r"\n{2,}|\n(?=\d+\.\s)|\n(?=[a-z]\)\s)", body_text)
                if p.strip()
            ]
            sub_buffer = ""
            for para in paragraphs:
                if len(sub_buffer) + len(para) + 1 <= self.max_chunk_size:
                    sub_buffer = f"{sub_buffer}\n\n{para}".strip()
                    continue
                if sub_buffer:
                    emit_chunk(sub_buffer, prefix, heading_path)
                    sub_buffer = ""
                if len(para) > self.max_chunk_size:
                    for part in self.split_oversized_paragraph(para, max_chunk_size=self.max_chunk_size, overlap=0):
                        emit_chunk(part, prefix, heading_path)
                else:
                    sub_buffer = para

            if sub_buffer:
                emit_chunk(sub_buffer, prefix, heading_path)

        for page_data in pages:
            page_number = int(page_data.get("page_number", 1))
            text = str(page_data.get("cleaned_text") or page_data.get("text") or "")
            lines = text.split("\n")
            line_idx = 0

            while line_idx < len(lines):
                stripped = lines[line_idx].strip()
                line_idx += 1
                if not stripped:
                    if article_lines and article_lines[-1] != "":
                        article_lines.append("")
                    continue

                if chap_match := self.CHAPTER_PATTERN.match(stripped):
                    flush_article_chunk()
                    current_chapter, line_idx = self._read_heading_with_lookahead(lines, line_idx, chap_match, "Chương")
                    current_section = ""
                    current_article = ""
                    article_page = page_number
                elif sec_match := self.SECTION_PATTERN.match(stripped):
                    flush_article_chunk()
                    current_section, line_idx = self._read_heading_with_lookahead(lines, line_idx, sec_match, "Mục")
                    current_article = ""
                    article_page = page_number
                elif art_match := self.ARTICLE_PATTERN.match(stripped):
                    flush_article_chunk()
                    art_title = (art_match.group(2) or "").strip(": .-")
                    current_article = f"Điều {art_match.group(1)}" + (f": {art_title}" if art_title else "")
                    article_page = page_number
                    article_lines.append(stripped)
                else:
                    article_lines.append(stripped)

        flush_article_chunk()
        return chunks


def get_chunker(
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> BaseChunker:
    """Instantiate and return the appropriate chunker based on requested strategy."""
    if strategy == "legal_structural":
        return LegalStructuralChunker(document_title=document_title, max_chunk_size=chunk_size)
    return RecursiveTextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def chunk_with_strategy(
    pages: list[dict[str, Any]],
    strategy: str = "legal_structural",
    document_title: str | None = None,
    chunk_size: int = settings.CHUNK_SIZE,
    chunk_overlap: int = settings.CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    """Split text pages using the requested chunking strategy."""
    chunker = get_chunker(
        strategy=strategy,
        document_title=document_title,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return chunker.chunk_pages(pages)


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
