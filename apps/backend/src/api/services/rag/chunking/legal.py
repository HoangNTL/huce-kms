"""Structure-aware chunker for Vietnamese/English academic regulations."""

import re
from typing import Any

from api.core.config import settings
from api.services.rag.chunking.base import BaseChunker
from api.services.rag.chunking.recursive import RecursiveTextChunker
from api.services.rag.patterns import (
    APPENDIX_PATTERN,
    ARTICLE_PATTERN,
    ATTACHED_FORM_PATTERN,
    ATTACHMENT_META_PATTERN,
    CEREMONIAL_BOILERPLATE_PATTERNS,
    CHAPTER_PATTERN,
    CLAUSE_NO_PATTERN,
    CLAUSE_OR_LIST_PATTERN,
    DOC_NUMBER_RE,
    ISSUED_DATE_RE,
    REGULATION_START_PATTERN,
    SECTION_PATTERN,
    STRUCTURAL_LINE_RE,
    SUB_ITEM_BREAK_PATTERN,
    TABLE_CAPTION_PATTERN,
    strip_markdown_markers,
)

_SIGNATURE_PREFIX_RE = re.compile(
    r"^(?:PGS|GS|TS|ThS|KT\.|TL\.|HIỆU TRƯỞNG|PHÓ HIỆU TRƯỞNG|Nơi nhận)"
)
_MD_SEP_ROW_RE = re.compile(r"^\|(?:\s*-{3,}\s*\|)+$")


class LegalStructuralChunker(BaseChunker):
    """Structure-aware chunker for Vietnamese regulations (Chương -> Mục -> Điều -> Khoản / Phụ lục)."""

    CHAPTER_PATTERN = CHAPTER_PATTERN
    SECTION_PATTERN = SECTION_PATTERN
    ARTICLE_PATTERN = ARTICLE_PATTERN
    APPENDIX_PATTERN = APPENDIX_PATTERN
    REGULATION_START_PATTERN = REGULATION_START_PATTERN
    ATTACHMENT_META_PATTERN = ATTACHMENT_META_PATTERN
    TABLE_CAPTION_PATTERN = TABLE_CAPTION_PATTERN
    CLAUSE_OR_LIST_PATTERN = CLAUSE_OR_LIST_PATTERN
    CLAUSE_NO_PATTERN = CLAUSE_NO_PATTERN
    SUB_ITEM_BREAK_PATTERN = SUB_ITEM_BREAK_PATTERN

    def __init__(
        self,
        document_title: str | None = None,
        max_chunk_size: int = settings.CHUNK_SIZE,
    ):
        self.document_title = document_title.strip() if document_title else None
        self.max_chunk_size = max(200, max_chunk_size)

    @staticmethod
    def _strip_markdown_markers(line: str) -> str:
        return strip_markdown_markers(line)

    def _has_legal_structure(self, pages: list[dict[str, Any]]) -> bool:
        """Check if pages contain any Article, Chapter, or Appendix patterns."""
        for page in pages:
            text = str(page.get("cleaned_text") or page.get("text") or "")
            for line in text.split("\n"):
                clean_line = strip_markdown_markers(line)
                if (
                    CHAPTER_PATTERN.match(clean_line)
                    or ARTICLE_PATTERN.match(clean_line)
                    or APPENDIX_PATTERN.match(clean_line)
                ):
                    return True
        return False

    def _is_heading_line(self, line: str) -> bool:
        clean_line = strip_markdown_markers(line)
        return any(
            pat.match(clean_line)
            for pat in (
                CHAPTER_PATTERN,
                SECTION_PATTERN,
                ARTICLE_PATTERN,
                APPENDIX_PATTERN,
                REGULATION_START_PATTERN,
            )
        )

    def _read_heading_with_lookahead(
        self,
        lines: list[str],
        next_idx: int,
        match: re.Match[str],
        label: str,
        num_group: int = 1,
        title_group: int = 2,
    ) -> tuple[str, list[str], int]:
        """Extract heading label + title, returning (heading, consumed_title_lines, next_idx)."""
        num = match.group(num_group)
        inline_title = (match.group(title_group) or "").strip(": .-")
        had_inline = bool(inline_title)
        title_parts = [inline_title] if inline_title else []
        consumed_lines: list[str] = []

        if not had_inline or inline_title.isupper():
            probe_idx = next_idx
            while probe_idx < len(lines) and len(title_parts) < 3:
                skipped_blank = False
                if not lines[probe_idx].strip():
                    if probe_idx + 1 >= len(lines):
                        break
                    after_blank = strip_markdown_markers(lines[probe_idx + 1])
                    if title_parts and not (after_blank and after_blank.isupper()):
                        break
                    probe_idx += 1
                    skipped_blank = True

                candidate = strip_markdown_markers(lines[probe_idx])
                is_title_candidate = (
                    bool(candidate)
                    and not self._is_heading_line(candidate)
                    and not CLAUSE_OR_LIST_PATTERN.match(candidate)
                    and not STRUCTURAL_LINE_RE.match(candidate)
                    and not ATTACHMENT_META_PATTERN.match(candidate)
                    and not _SIGNATURE_PREFIX_RE.match(candidate)
                    and not ATTACHED_FORM_PATTERN.match(candidate)
                    and (not skipped_blank or (len(candidate) <= 120 and not candidate.endswith(".")))
                    and (
                        (candidate.isupper() and len(candidate) <= 120 and not candidate.endswith("."))
                        if had_inline
                        else (not title_parts or (candidate.isupper() and len(candidate) <= 120))
                    )
                )
                if not is_title_candidate:
                    break
                title_parts.append(candidate)
                consumed_lines.append(lines[probe_idx].strip())
                probe_idx += 1
                next_idx = probe_idx

        title = " ".join(title_parts).strip()
        heading = f"{label} {num}" + (f": {title}" if title else "")
        return heading, consumed_lines, next_idx

    @classmethod
    def _split_lines_into_paragraphs(
        cls, line_items: list[tuple[int, str]], max_chunk_size: int
    ) -> list[tuple[int, int, str, list[tuple[int, str]]]]:
        """Group article lines into (page_start, page_end, paragraph_text, line_items) blocks."""
        raw_blocks: list[list[tuple[int, str]]] = []
        current_lines: list[tuple[int, str]] = []
        in_table = False

        def flush_block() -> None:
            nonlocal current_lines, in_table
            if current_lines:
                raw_blocks.append(current_lines)
                current_lines = []
            in_table = False

        for page_num, text in line_items:
            stripped = text.strip()
            if not stripped:
                flush_block()
                continue

            is_table_line = stripped.startswith("|")
            if is_table_line != in_table:
                flush_block()
                in_table = is_table_line
            elif not is_table_line and current_lines and SUB_ITEM_BREAK_PATTERN.match(stripped):
                flush_block()

            current_lines.append((page_num, stripped))

        flush_block()

        paragraphs = [
            (min(p for p, _ in blk), max(p for p, _ in blk), "\n".join(t for _, t in blk).strip(), blk)
            for blk in raw_blocks
            if blk
        ]

        # Merge lead-in lines ending with ':' or table captions with immediate list/table if it fits
        merged: list[tuple[int, int, str, list[tuple[int, str]]]] = []
        idx = 0
        while idx < len(paragraphs):
            p_start, p_end, p_text, p_items = paragraphs[idx]
            if idx + 1 < len(paragraphs):
                next_start, next_end, next_text, next_items = paragraphs[idx + 1]
                is_lead_in = p_text.endswith(":") and (
                    CLAUSE_OR_LIST_PATTERN.match(next_text) or next_text.startswith("|")
                )
                is_table_caption = (
                    len(p_text) <= 180
                    and bool(TABLE_CAPTION_PATTERN.match(p_text))
                    and next_text.startswith("|")
                )
                if (is_lead_in or is_table_caption) and len(p_text) + len(next_text) + 2 <= max_chunk_size:
                    merged.append((
                        min(p_start, next_start),
                        max(p_end, next_end),
                        f"{p_text}\n\n{next_text}".strip(),
                        [*p_items, (p_end, ""), *next_items],
                    ))
                    idx += 2
                    continue
            merged.append((p_start, p_end, p_text, p_items))
            idx += 1

        return merged

    @staticmethod
    def _is_attachment_title_candidate(line: str) -> bool:
        """Return True if line looks like an attached document title line before '(Kèm theo...)'."""
        stripped = line.strip()
        if not stripped or len(stripped) > 140 or stripped.startswith("|") or ":" in stripped:
            return False
        if stripped.endswith(".") and not stripped.isupper():
            return False
        if _SIGNATURE_PREFIX_RE.match(stripped):
            return False
        return stripped.isupper() or stripped.istitle() or sum(1 for c in stripped if c.isupper()) >= 3

    @staticmethod
    def _handle_page_transition(
        article_lines: list[tuple[int, str]], lines: list[str], page_number: int
    ) -> int:
        """Preserve table/paragraph boundaries across page breaks and merge multi-page tables cleanly."""
        if not article_lines or article_lines[-1][1] == "":
            return 0
        first_idx = next((i for i, l in enumerate(lines) if l.strip()), None)
        if first_idx is None:
            return 0

        last_line = article_lines[-1][1]
        first_line = lines[first_idx].strip()
        if last_line.startswith("|") and first_line.startswith("|"):
            if last_line.count("|") == first_line.count("|"):
                tbl_start = len(article_lines) - 1
                while tbl_start > 0 and article_lines[tbl_start - 1][1].startswith("|"):
                    tbl_start -= 1
                prev_header = article_lines[tbl_start][1].strip()
                if first_idx + 1 < len(lines) and _MD_SEP_ROW_RE.match(lines[first_idx + 1].strip()):
                    if first_line != prev_header:
                        # 1-row / headless continuation: keep data row and drop synthetic separator
                        article_lines.append((page_number, first_line))
                        return first_idx + 2
                    skip = first_idx + 2
                    offset = 2
                    while (
                        skip < len(lines)
                        and tbl_start + offset < len(article_lines)
                        and offset < 4
                        and lines[skip].strip() == article_lines[tbl_start + offset][1].strip()
                    ):
                        skip += 1
                        offset += 1
                    return skip
        elif last_line.startswith("|") or first_line.startswith("|"):
            article_lines.append((page_number, ""))
        return 0

    @staticmethod
    def _strip_ceremonial_boilerplate(text: str) -> str:
        """Strip ceremonial header lines ('CỘNG HÒA XHCN...', 'Độc lập - Tự do...') from preamble."""
        kept = [
            line
            for line in text.split("\n")
            if not any(pat.match(line.strip()) for pat in CEREMONIAL_BOILERPLATE_PATTERNS)
        ]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()

    @staticmethod
    def _extract_preamble_metadata(text: str) -> dict[str, Any]:
        """Extract doc_number and issued_date from administrative preamble text."""
        extra: dict[str, Any] = {"chunk_type": "preamble"}
        if num_match := DOC_NUMBER_RE.search(text):
            raw_num = (num_match.group(1) or num_match.group(2) or "").strip()
            if raw_num:
                extra["doc_number"] = re.sub(r"\s*/\s*", "/", raw_num)
        if date_match := ISSUED_DATE_RE.search(text):
            day, month, year = date_match.groups()
            extra["issued_date"] = f"{int(day):02d}/{int(month):02d}/{year}"
        return extra

    def chunk_pages(self, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Chunk pages hierarchically with clean content separated from context & metadata."""
        if not self._has_legal_structure(pages):
            return RecursiveTextChunker(
                chunk_size=self.max_chunk_size,
                document_title=self.document_title,
            ).chunk_pages(pages)

        chunks: list[dict[str, Any]] = []
        state: dict[str, Any] = {
            "chapter": "",
            "section": "",
            "article": "",
            "article_no": None,
            "article_title": None,
            "appendix_no": None,
        }
        article_lines: list[tuple[int, str]] = []

        def reset_scope(from_level: str) -> None:
            if from_level in ("root", "chapter", "appendix"):
                state["chapter"] = ""
            if from_level in ("root", "chapter", "section", "appendix"):
                state["section"] = ""
            state["article"] = ""
            state["article_no"] = None
            state["article_title"] = None
            if from_level in ("root", "chapter", "article"):
                state["appendix_no"] = None

        def build_chunk_metadata(body: str, p_start: int, p_end: int) -> dict[str, Any]:
            meta: dict[str, Any] = {"page_start": p_start, "page_end": p_end}
            for key in ("chapter", "section", "article_no", "article_title", "appendix_no"):
                if state[key] not in ("", None):
                    meta[key] = state[key]
            clauses = list(dict.fromkeys(m.group(1) for m in CLAUSE_NO_PATTERN.finditer(body)))
            if clauses:
                meta["clauses"] = clauses
            return meta

        def flush_article_chunk() -> None:
            nonlocal article_lines
            if not article_lines:
                return
            items = article_lines
            article_lines = []

            paragraphs = self._split_lines_into_paragraphs(items, self.max_chunk_size)
            if not paragraphs:
                return

            heading_path = " > ".join(p for p in (state["chapter"], state["section"], state["article"]) if p)
            context_str = " > ".join(p for p in (self.document_title, heading_path) if p)

            packed = self.pack_blocks(
                paragraphs,
                max_chunk_size=self.max_chunk_size,
                sep="\n\n",
                split_oversized=lambda _ps, _pe, _txt, p_items: self.split_oversized_paragraph_with_pages(
                    p_items, max_chunk_size=self.max_chunk_size, overlap=0
                ),
            )
            for p_start, p_end, body in packed:
                is_root_preamble = (
                    len(chunks) == 0
                    and state["article"] == ""
                    and state["appendix_no"] is None
                    and state["chapter"] == ""
                )
                extra_meta: dict[str, Any] = {}
                if is_root_preamble:
                    extra_meta = self._extract_preamble_metadata(body)
                    body = self._strip_ceremonial_boilerplate(body)
                    if not body:
                        continue
                meta = build_chunk_metadata(body, p_start, p_end)
                meta.update(extra_meta)
                chunks.append(
                    self._make_chunk(
                        chunk_index=len(chunks),
                        content=body,
                        page_start=p_start,
                        page_end=p_end,
                        heading_path=heading_path,
                        context=context_str,
                        metadata=meta,
                    )
                )

        for page_data in pages:
            page_number = int(page_data.get("page_number", 1))
            lines = str(page_data.get("cleaned_text") or page_data.get("text") or "").split("\n")
            line_idx = self._handle_page_transition(article_lines, lines, page_number)

            while line_idx < len(lines):
                stripped = lines[line_idx].strip()
                line_idx += 1
                if not stripped:
                    if article_lines and article_lines[-1][1] != "":
                        article_lines.append((page_number, ""))
                    continue

                clean_line = strip_markdown_markers(stripped)

                if chap_match := CHAPTER_PATTERN.match(clean_line):
                    flush_article_chunk()
                    reset_scope("chapter")
                    state["chapter"], _, line_idx = self._read_heading_with_lookahead(lines, line_idx, chap_match, "Chương")
                elif sec_match := SECTION_PATTERN.match(clean_line):
                    flush_article_chunk()
                    reset_scope("section")
                    state["section"], _, line_idx = self._read_heading_with_lookahead(lines, line_idx, sec_match, "Mục")
                elif app_match := APPENDIX_PATTERN.match(clean_line):
                    flush_article_chunk()
                    reset_scope("appendix")
                    label = "Appendix" if app_match.group(1).lower().startswith("appendix") else "Phụ lục"
                    state["appendix_no"] = app_match.group(2)
                    state["article"], consumed, line_idx = self._read_heading_with_lookahead(
                        lines, line_idx, app_match, label, num_group=2, title_group=3
                    )
                    state["article_title"] = state["article"].split(":", 1)[1].strip() if ":" in state["article"] else None
                    article_lines.append((page_number, clean_line))
                    article_lines.extend((page_number, t) for t in consumed)
                elif art_match := ARTICLE_PATTERN.match(clean_line):
                    flush_article_chunk()
                    reset_scope("article")
                    art_num = int(art_match.group(1))
                    art_title = (art_match.group(2) or "").strip(": .-")
                    if art_title and not art_title.endswith((".", ":", "!", "?")) and line_idx < len(lines):
                        next_clean = strip_markdown_markers(lines[line_idx])
                        if (
                            next_clean
                            and len(next_clean) <= 160
                            and not next_clean.startswith("|")
                            and not self._is_heading_line(next_clean)
                            and not CLAUSE_OR_LIST_PATTERN.match(next_clean)
                            and not ATTACHMENT_META_PATTERN.match(next_clean)
                            and not _SIGNATURE_PREFIX_RE.match(next_clean)
                            and not ATTACHED_FORM_PATTERN.match(next_clean)
                            and not next_clean.endswith((".", ":", ";", "!", "?"))
                        ):
                            art_title = f"{art_title} {next_clean}"
                    state["article_no"] = art_num
                    state["article_title"] = art_title or None
                    state["article"] = f"Điều {art_num}" + (f": {art_title}" if art_title else "")
                    article_lines.append((page_number, clean_line))
                elif (
                    ATTACHMENT_META_PATTERN.match(clean_line)
                    and (state["article_no"] is not None or state["appendix_no"] is not None)
                    and sum(1 for _, l in article_lines if l.strip()) > 4
                ):
                    peeled: list[tuple[int, str]] = []
                    title_count = 0
                    while article_lines and title_count < 4:
                        if not article_lines[-1][1].strip():
                            if not peeled:
                                article_lines.pop()
                                continue
                            # Peek past a single blank line to catch multi-line title wrapped across page break
                            if len(article_lines) >= 2 and self._is_attachment_title_candidate(article_lines[-2][1]):
                                peeled.append(article_lines.pop())
                                continue
                            break
                        if not self._is_attachment_title_candidate(article_lines[-1][1]):
                            break
                        peeled.append(article_lines.pop())
                        title_count += 1
                    peeled.reverse()

                    flush_article_chunk()
                    reset_scope("root")
                    article_lines.extend(peeled)
                    article_lines.append((page_number, stripped))
                elif REGULATION_START_PATTERN.match(clean_line) and state["article"]:
                    flush_article_chunk()
                    reset_scope("root")
                    article_lines.append((page_number, stripped))
                elif (
                    ATTACHED_FORM_PATTERN.match(clean_line)
                    and state["article"]
                    and any(_SIGNATURE_PREFIX_RE.match(strip_markdown_markers(l)) for _, l in article_lines)
                ):
                    flush_article_chunk()
                    reset_scope("root")
                    state["chapter"] = clean_line
                    article_lines.append((page_number, stripped))
                else:
                    article_lines.append((page_number, stripped))

        flush_article_chunk()
        return chunks
