import re
from typing import Any

from api.services.rag.chunkers.base import BaseChunker
from api.services.rag.chunkers.recursive import RecursiveTextChunker


class LegalStructuralChunker(BaseChunker):
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
            recursive_chunker = RecursiveTextChunker(chunk_size=self.max_chunk_size)
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
                    "token_count": self.estimate_tokens(enriched_content),
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
                                "token_count": self.estimate_tokens(enriched),
                                "overlap_preview": "",
                            })
                            global_chunk_index += 1
                            sub_buffer = ""

                        if len(para) > self.max_chunk_size:
                            sub_parts = self.split_oversized_paragraph(
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
                                    "token_count": self.estimate_tokens(enriched),
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
                        "token_count": self.estimate_tokens(enriched),
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
