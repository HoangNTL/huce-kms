"""Base chunker utilities: metadata builder, block packing, and Markdown table splitting."""

from abc import ABC, abstractmethod
from collections.abc import Callable
import hashlib
import re
from typing import Any

from api.services.rag.patterns import detect_language


class BaseChunker(ABC):
    """Abstract base class for document chunkers with common token, packing, and splitting utilities."""

    @abstractmethod
    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Split a list of parsed pages into semantic chunks."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for Vietnamese and English mixed text (~1.3 tokens/word)."""
        return max(1, int(len(text.split()) * 1.3))

    @staticmethod
    def compute_content_hash(content: str, context: str = "") -> str:
        """Compute deterministic SHA-256 hash of (context + content) for re-ingest diffing."""
        raw = f"{context}\n{content}".strip() if context else content.strip()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _make_chunk(
        cls,
        chunk_index: int,
        content: str,
        page_start: int,
        page_end: int | None = None,
        heading_path: str = "",
        context: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build a standardized chunk dictionary with clean content and structured metadata."""
        resolved_end = max(page_start, page_end if page_end is not None else page_start)
        meta = dict(metadata or {})
        meta.setdefault("page_start", page_start)
        meta.setdefault("page_end", resolved_end)
        clean_content = content.strip()
        resolved_context = context.strip() or heading_path.strip()
        if "language" not in meta:
            detected_lang = detect_language(clean_content)
            if detected_lang:
                meta["language"] = detected_lang

        return {
            "chunk_index": chunk_index,
            "heading_path": heading_path,
            "context": resolved_context,
            "content": clean_content,
            "metadata": meta,
            "page_number": page_start,
            "page_start": page_start,
            "page_end": resolved_end,
            "token_count": cls.estimate_tokens(clean_content),
            "content_hash": cls.compute_content_hash(clean_content, resolved_context),
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
        return (
            lines[0].startswith("|")
            and lines[0].endswith("|")
            and "---" in lines[1]
            and lines[1].startswith("|")
        )

    @classmethod
    def pack_blocks(
        cls,
        blocks: list[tuple[int, int, str, Any]],
        max_chunk_size: int,
        sep: str = "\n\n",
        split_oversized: Callable[[int, int, str, Any], list[tuple[int, int, str]]] | None = None,
    ) -> list[tuple[int, int, str]]:
        """Pack page-tracked blocks up to max_chunk_size, delegating oversized blocks when needed."""
        packed: list[tuple[int, int, str]] = []
        buf = ""
        buf_start = 0
        buf_end = 0

        for p_start, p_end, text, payload in blocks:
            if not text:
                continue
            if not buf:
                if len(text) <= max_chunk_size:
                    buf, buf_start, buf_end = text, p_start, p_end
                    continue
                if split_oversized:
                    packed.extend(split_oversized(p_start, p_end, text, payload))
                else:
                    packed.append((p_start, p_end, text))
                continue

            if len(buf) + len(sep) + len(text) <= max_chunk_size:
                buf = f"{buf}{sep}{text}"
                buf_end = max(buf_end, p_end)
                continue

            packed.append((buf_start, buf_end, buf))
            buf = ""
            if len(text) > max_chunk_size and split_oversized:
                packed.extend(split_oversized(p_start, p_end, text, payload))
            else:
                buf, buf_start, buf_end = text, p_start, p_end

        if buf:
            packed.append((buf_start, buf_end, buf))
        return packed

    @classmethod
    def _detect_table_header_count(cls, lines: list[str]) -> int:
        """Return 3 when a Markdown table has a repeatable table-wide merged header + sub-header."""
        if len(lines) < 4:
            return 2
        top_cells = [c.strip() for c in lines[0].strip("|").split("|")]
        sub_cells = [c.strip() for c in lines[2].strip("|").split("|")]
        has_empty_top = any(c == "" for c in top_cells)
        sub_is_compact = len(lines[2]) <= 220 and len(lines[3]) > len(lines[2])
        if has_empty_top and sub_is_compact and sub_cells and sub_cells[0] == "" and any(sub_cells):
            return 3
        return 2

    @classmethod
    def split_markdown_table_with_pages(
        cls, row_items: list[tuple[int, str]], max_chunk_size: int
    ) -> list[tuple[int, int, str]]:
        """Split an oversized Markdown table along row boundaries, repeating headers and tracking pages."""
        cleaned = [(p, line.strip()) for p, line in row_items if line.strip()]
        if not cleaned:
            return []
        lines = [line for _, line in cleaned]
        hdr_count = cls._detect_table_header_count(lines)
        if len(cleaned) <= hdr_count:
            return [(min(p for p, _ in cleaned), max(p for p, _ in cleaned), "\n".join(lines))]

        header_str = "\n".join(lines[:hdr_count])
        header_len = len(header_str)
        chunks: list[tuple[int, int, str]] = []
        current_rows: list[tuple[int, str]] = []
        current_len = header_len

        for page_num, row in cleaned[hdr_count:]:
            row_len = len(row) + 1
            is_single_label_row = (
                len(current_rows) == 1
                and len(current_rows[0][1]) <= 220
                and "." not in current_rows[0][1]
                and (current_len + row_len <= int(max_chunk_size * 1.25))
            )
            if current_rows and (current_len + row_len > max_chunk_size) and not is_single_label_row:
                chunks.append((
                    min(p for p, _ in current_rows),
                    max(p for p, _ in current_rows),
                    f"{header_str}\n" + "\n".join(r for _, r in current_rows),
                ))
                current_rows = [(page_num, row)]
                current_len = header_len + row_len
            else:
                current_rows.append((page_num, row))
                current_len += row_len

        if current_rows:
            chunks.append((
                min(p for p, _ in current_rows),
                max(p for p, _ in current_rows),
                f"{header_str}\n" + "\n".join(r for _, r in current_rows),
            ))
        return chunks

    @classmethod
    def split_markdown_table(cls, table_text: str, max_chunk_size: int) -> list[str]:
        """Split an oversized Markdown table along row boundaries, repeating the header rows."""
        lines = [line.strip() for line in table_text.strip().split("\n") if line.strip()]
        if len(lines) <= 2:
            return [table_text]
        return [t for _, _, t in cls.split_markdown_table_with_pages([(1, l) for l in lines], max_chunk_size)]

    @classmethod
    def split_oversized_paragraph_with_pages(
        cls,
        line_items: list[tuple[int, str]],
        max_chunk_size: int,
        overlap: int = 0,
    ) -> list[tuple[int, int, str]]:
        """Split an oversized line-tracked block while preserving exact page_start/page_end per part."""
        non_empty = [(p, line.strip()) for p, line in line_items if line.strip()]
        if not non_empty:
            return []

        full_text = "\n".join(line for _, line in non_empty)
        if cls.is_markdown_table(full_text):
            return cls.split_markdown_table_with_pages(non_empty, max_chunk_size)
        if len(full_text) <= max_chunk_size:
            return [(min(p for p, _ in non_empty), max(p for p, _ in non_empty), full_text)]

        if len(non_empty) == 1:
            p_num = non_empty[0][0]
            return [(p_num, p_num, sub) for sub in cls.split_oversized_paragraph(full_text, max_chunk_size, overlap)]

        blocks = [(p, p, line, None) for p, line in non_empty]
        return cls.pack_blocks(
            blocks,
            max_chunk_size=max_chunk_size,
            sep="\n",
            split_oversized=lambda ps, pe, txt, _: [
                (ps, pe, sub) for sub in cls.split_oversized_paragraph(txt, max_chunk_size, overlap)
            ],
        )

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
            remaining = remaining[step_back or cut_idx :].strip()

        return parts
