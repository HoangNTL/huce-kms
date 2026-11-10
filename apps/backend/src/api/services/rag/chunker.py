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
        cleaned = re.sub(r"\r\n|\r", "\n", text)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
        return paragraphs if paragraphs else [cleaned.strip()]

    @classmethod
    def is_markdown_table(cls, text: str) -> bool:
        """Check if a text block represents a Markdown table."""
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
        repeating the table header row on every chunk.
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
            row_len = len(row) + 1  # newline
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
        Split a paragraph that exceeds max_chunk_size.
        If it's a Markdown table, splits row by row keeping headers.
        Otherwise, splits along word/sentence boundaries rather than cutting words in half.
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

            current_chunk = ""

            for para in paragraphs:
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

    @classmethod
    def chunk_with_strategy(
        cls,
        pages: list[dict[str, Any]],
        strategy: str = "legal_structural",
        document_title: str | None = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> list[dict[str, Any]]:
        """Factory method to split text pages using the requested chunking strategy."""
        if strategy == "legal_structural":
            chunker = LegalStructuralChunker(
                document_title=document_title,
                max_chunk_size=chunk_size,
            )
            return chunker.chunk_pages(pages)

        # Default recursive chunker
        chunker = cls(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return chunker.chunk_pages(pages)

    @classmethod
    def generate_chunk_preview(
        cls,
        text: str | None = None,
        pages: list[dict[str, Any]] | None = None,
        strategy: str = "legal_structural",
        document_title: str | None = None,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ) -> "ChunkPreviewResponse":
        """Process text/pages and return structured chunking preview with token analytics."""
        from api.core.exceptions import BadRequestException
        from api.schemas.rag_preview import ChunkPreviewItem, ChunkPreviewResponse

        if pages:
            input_pages = pages
        elif text and text.strip():
            input_pages = [{"page_number": 1, "text": text.strip()}]
        else:
            raise BadRequestException(message="Either 'text' or 'pages' must be provided for chunk preview.")

        raw_chunks = cls.chunk_with_strategy(
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


class LegalStructuralChunker:
    """
    Structure-aware chunker specialized for Vietnamese university academic regulations and legal notices.
    Splits text along administrative boundaries (Chương -> Mục -> Điều -> Khoản)
    and enriches each chunk with hierarchical breadcrumb context.
    """

    CHAPTER_PATTERN = re.compile(
        r"^(?:CHƯƠNG|Chương)\s+([IVXLCDM\d]+)(?:\s*[:\.\-]\s*(.*))?$",
        re.MULTILINE,
    )
    SECTION_PATTERN = re.compile(
        r"^(?:MỤC|Mục)\s+(\d+)(?:\s*[:\.\-]\s*(.*))?$",
        re.MULTILINE,
    )
    ARTICLE_PATTERN = re.compile(
        r"^(?:ĐIỀU|Điều)\s+(\d+)(?:\s*[:\.\-]\s*(.*))?$",
        re.MULTILINE,
    )

    def __init__(
        self,
        document_title: str | None = None,
        max_chunk_size: int = 1200,
    ):
        self.document_title = document_title.strip() if document_title else None
        self.max_chunk_size = max(200, max_chunk_size)

    def _has_legal_structure(self, pages: list[dict[str, Any]]) -> bool:
        """Check if pages contain any Article or Chapter patterns."""
        for p in pages:
            text = str(p.get("cleaned_text") or p.get("text") or "")
            if self.ARTICLE_PATTERN.search(text) or self.CHAPTER_PATTERN.search(text):
                return True
        return False

    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Chunk pages hierarchically by regulation articles with contextual breadcrumbs."""
        if not self._has_legal_structure(pages):
            # Graceful fallback to recursive character chunker
            recursive_chunker = TextChunker(chunk_size=self.max_chunk_size)
            return recursive_chunker.chunk_pages(pages)

        chunks: list[dict[str, Any]] = []
        global_chunk_index = 0

        current_chapter = ""
        current_section = ""
        current_article = ""
        article_page = 1
        article_lines: list[str] = []

        def flush_article_chunk():
            nonlocal global_chunk_index, article_lines
            if not article_lines:
                return

            body_text = "\n".join(article_lines).strip()
            article_lines = []
            if not body_text:
                return

            # Construct breadcrumb path
            path_parts = [p for p in [current_chapter, current_section, current_article] if p]
            heading_path = " > ".join(path_parts) if path_parts else (self.document_title or "")

            # Construct contextual prefix
            prefix_parts = []
            if self.document_title:
                prefix_parts.append(f"[Tài liệu: {self.document_title}]")
            if heading_path:
                prefix_parts.append(f"[{heading_path}]")
            prefix = " ".join(prefix_parts) + "\n" if prefix_parts else ""

            # Check if article body exceeds max_chunk_size
            if len(body_text) <= self.max_chunk_size:
                enriched_content = f"{prefix}{body_text}".strip()
                chunks.append({
                    "chunk_index": global_chunk_index,
                    "heading_path": heading_path,
                    "content": enriched_content,
                    "page_number": article_page,
                    "token_count": TextChunker.estimate_tokens(enriched_content),
                    "overlap_preview": "",
                })
                global_chunk_index += 1
            else:
                # Sub-split long article by paragraphs or numbered clauses (1., 2., 3., a), b))
                paragraphs = [
                    p.strip()
                    for p in re.split(r"\n{2,}|\n(?=\d+\.\s)|\n(?=[a-z]\)\s)", body_text)
                    if p.strip()
                ]
                sub_buffer = ""
                for para in paragraphs:
                    if len(sub_buffer) + len(para) + 1 <= self.max_chunk_size:
                        sub_buffer = f"{sub_buffer}\n\n{para}".strip()
                    else:
                        if sub_buffer:
                            enriched = f"{prefix}{sub_buffer}".strip()
                            chunks.append({
                                "chunk_index": global_chunk_index,
                                "heading_path": heading_path,
                                "content": enriched,
                                "page_number": article_page,
                                "token_count": TextChunker.estimate_tokens(enriched),
                                "overlap_preview": "",
                            })
                            global_chunk_index += 1
                            sub_buffer = ""

                        if len(para) > self.max_chunk_size:
                            sub_parts = TextChunker.split_oversized_paragraph(
                                para=para,
                                max_chunk_size=self.max_chunk_size,
                                overlap=0,
                            )
                            for part in sub_parts:
                                enriched = f"{prefix}{part}".strip()
                                chunks.append({
                                    "chunk_index": global_chunk_index,
                                    "heading_path": heading_path,
                                    "content": enriched,
                                    "page_number": article_page,
                                    "token_count": TextChunker.estimate_tokens(enriched),
                                    "overlap_preview": "",
                                })
                                global_chunk_index += 1
                        else:
                            sub_buffer = para

                if sub_buffer:
                    enriched = f"{prefix}{sub_buffer}".strip()
                    chunks.append({
                        "chunk_index": global_chunk_index,
                        "heading_path": heading_path,
                        "content": enriched,
                        "page_number": article_page,
                        "token_count": TextChunker.estimate_tokens(enriched),
                        "overlap_preview": "",
                    })
                    global_chunk_index += 1

        # Scan text line by line across pages
        for page_data in pages:
            page_number = int(page_data.get("page_number", 1))
            text = str(page_data.get("cleaned_text") or page_data.get("text") or "")
            lines = text.split("\n")
            line_idx = 0

            while line_idx < len(lines):
                line = lines[line_idx]
                line_idx += 1
                stripped = line.strip()
                if not stripped:
                    if article_lines and article_lines[-1] != "":
                        article_lines.append("")
                    continue

                # Check Chapter pattern
                chap_match = self.CHAPTER_PATTERN.match(stripped)
                if chap_match:
                    flush_article_chunk()
                    chap_num = chap_match.group(1)
                    chap_title = (chap_match.group(2) or "").strip(": .-")
                    # If chapter title is on the next line, look ahead to capture it
                    if not chap_title and line_idx < len(lines):
                        next_stripped = lines[line_idx].strip()
                        if (
                            next_stripped
                            and not self.CHAPTER_PATTERN.match(next_stripped)
                            and not self.SECTION_PATTERN.match(next_stripped)
                            and not self.ARTICLE_PATTERN.match(next_stripped)
                        ):
                            chap_title = next_stripped
                            line_idx += 1

                    current_chapter = f"Chương {chap_num}" + (f": {chap_title}" if chap_title else "")
                    current_section = ""
                    current_article = ""
                    article_page = page_number
                    continue

                # Check Section pattern
                sec_match = self.SECTION_PATTERN.match(stripped)
                if sec_match:
                    flush_article_chunk()
                    sec_num = sec_match.group(1)
                    sec_title = (sec_match.group(2) or "").strip(": .-")
                    # If section title is on the next line, look ahead to capture it
                    if not sec_title and line_idx < len(lines):
                        next_stripped = lines[line_idx].strip()
                        if (
                            next_stripped
                            and not self.CHAPTER_PATTERN.match(next_stripped)
                            and not self.SECTION_PATTERN.match(next_stripped)
                            and not self.ARTICLE_PATTERN.match(next_stripped)
                        ):
                            sec_title = next_stripped
                            line_idx += 1

                    current_section = f"Mục {sec_num}" + (f": {sec_title}" if sec_title else "")
                    current_article = ""
                    article_page = page_number
                    continue

                # Check Article pattern
                art_match = self.ARTICLE_PATTERN.match(stripped)
                if art_match:
                    flush_article_chunk()
                    art_num = art_match.group(1)
                    art_title = (art_match.group(2) or "").strip(": .-")
                    current_article = f"Điều {art_num}" + (f": {art_title}" if art_title else "")
                    article_page = page_number
                    article_lines.append(stripped)
                    continue

                # Standard line inside article
                article_lines.append(stripped)

        # Flush any trailing article
        flush_article_chunk()

        return chunks
