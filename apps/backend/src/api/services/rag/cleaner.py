import re
import unicodedata
from typing import Any

from api.services.rag.patterns import (
    BARE_PAGE_NUMBER_RE,
    FORM_BLANK_RE,
    HEADING_LINE_RE,
    REPEATED_COMMA_RE,
    STRUCTURAL_LINE_RE,
    VN_ACCENTED_LOWER,
    sanitize_pdf_symbols,
)

# Standalone Vietnamese consonant onsets/codas that are never valid standalone words
_SYLLABLE_REPAIR_PATTERNS = (
    re.compile(
        r"(?<![A-Za-zÀ-ỹ0-9/])(ch|kh|ph|gh|ngh|nh|th|tr|qu|gi|đ)\s+"
        rf"([{VN_ACCENTED_LOWER}aăâeêioôơuưy][a-zà-ỹ]*)\b"
    ),
    re.compile(
        r"(?<![A-Za-zÀ-ỹ0-9/])([bcdghklmnpqrstvx]|Th|Ch|Ph|Kh|Gh|Ngh|Nh|Tr|Qu|Đ)\s+"
        rf"([{VN_ACCENTED_LOWER}][a-zà-ỹ]*)\b"
    ),
    re.compile(
        rf"\b([A-Za-zÀ-ỹ]*[{VN_ACCENTED_LOWER}][a-zà-ỹ]*)\s+"
        r"(ng|nh|ch|[cmnpt])(?![A-Za-zÀ-ỹ.)/])"
    ),
)

_DANGLING_CONNECTORS = frozenset({
    "và", "của", "về", "trong", "cho", "với", "tại", "theo", "bởi", "từ",
    "đến", "trên", "dưới", "các", "những", "giữa", "hoặc", "như", "nên",
    "of", "and", "in", "the", "to", "for", "by", "with", "from", "at",
    "on", "or", "among", "between", "into", "through", "including",
})


class TextCleaner:
    """Pre-processing and text sanitization pipeline for Vietnamese academic documents."""

    NOISE_PATTERNS = [
        re.compile(r"^\s*Trang\s+\d+(\s*[/_\\-]\s*\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*-\s*\d+\s*-\s*$"),
        re.compile(r"^\s*Page\s+\d+(\s*of\s*\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*\[\s*\d+\s*\]\s*$"),
    ]

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Vietnamese text to canonical NFC Unicode and clean PUA/invisible glyphs."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", sanitize_pdf_symbols(text))

    @staticmethod
    def repair_broken_spacing(text: str) -> str:
        """Repair split Vietnamese syllables, stray punctuation, and form dot-fill blanks."""
        if not text:
            return ""
        repaired = FORM_BLANK_RE.sub("...", text)
        repaired = REPEATED_COMMA_RE.sub(", ", repaired)
        repaired = re.sub(r"(\d+)\s+/(?=[A-ZÀ-Ỹ]{2,})", r"\1/", repaired)
        repaired = re.sub(r"\s+([,;:.!?])(?=\s|$|<br>)", r"\1", repaired)
        for _ in range(2):
            for pat in _SYLLABLE_REPAIR_PATTERNS:
                repaired = pat.sub(r"\1\2", repaired)
        return re.sub(r"(?<!\.)\.\.(?!\.)", ".", repaired)

    @classmethod
    def _should_merge_soft_break(cls, prev_line: str, curr_line: str) -> bool:
        """Return True when curr_line is a soft-wrapped continuation of prev_line."""
        if not prev_line or not curr_line or prev_line.startswith("|") or curr_line.startswith("|"):
            return False
        if STRUCTURAL_LINE_RE.match(curr_line) or HEADING_LINE_RE.match(prev_line):
            return False
        if prev_line.endswith((".", "!", "?", ":")):
            return False
        if curr_line[0].islower():
            return True
        if curr_line.isupper() and len(curr_line) > 4:
            return False
        if prev_line.endswith((",", "(")):
            return True
        return prev_line.rstrip(".,;:()").rsplit(None, 1)[-1].lower() in _DANGLING_CONNECTORS

    @classmethod
    def _filter_page_noise(cls, lines: list[str]) -> tuple[list[str], list[str]]:
        """Remove edge page numbers and pagination noise lines."""
        non_empty = [i for i, l in enumerate(lines) if l.strip()]
        edge_num_indices = {
            idx
            for idx in (non_empty[:1] + non_empty[-1:])
            if BARE_PAGE_NUMBER_RE.match(lines[idx])
        }
        retained: list[str] = []
        removed: list[str] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                retained.append("")
            elif idx in edge_num_indices or any(p.match(stripped) for p in cls.NOISE_PATTERNS):
                removed.append(stripped)
            else:
                retained.append(stripped)
        return retained, removed

    @classmethod
    def clean_page_text(cls, text: str) -> tuple[str, list[str]]:
        """Sanitize raw page text: NFC normalize, strip noise, de-hyphenate, and repair spacing."""
        if not text:
            return "", []

        normalized = cls.normalize_unicode(text).replace("\r\n", "\n").replace("\r", "\n")
        retained, removed_noise = cls._filter_page_noise(normalized.split("\n"))
        joined = "\n".join(retained)
        joined = re.sub(r"([A-Z0-9]+)-\n([A-Z0-9]+)", r"\1-\2", joined)
        joined = re.sub(r"([a-zà-ỹ]{2,})-\n([a-zà-ỹ]{2,})", r"\1\2", joined)
        # Attach standalone PDF bullet lines (e.g. "-\nItem text") onto their following item line
        joined = re.sub(r"(?m)^([-•*–])[ \t]*\n+(?![|\-*•–\s])", r"\1 ", joined)

        merged: list[str] = []
        for line in joined.split("\n"):
            stripped = line.strip()
            if not stripped:
                merged.append("")
            elif merged and merged[-1] and cls._should_merge_soft_break(merged[-1], stripped):
                merged[-1] = f"{merged[-1]} {stripped}"
            else:
                merged.append(stripped)

        collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(merged))
        cleaned_lines = []
        for l in collapsed.split("\n"):
            cleaned_line = cls.repair_broken_spacing(re.sub(r"[ \t]+", " ", l).strip())
            if cleaned_line and re.fullmatch(r"\.{3,}", cleaned_line):
                continue
            cleaned_lines.append(cleaned_line)
        return "\n".join(cleaned_lines).strip(), removed_noise

    @classmethod
    def _strip_repeated_headers_footers(cls, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove identical running headers/footers repeated across >= half of pages (min 3 pages)."""
        if len(pages) < 3:
            return pages

        def _sig(line: str) -> str:
            return re.sub(r"\d+", "#", line.strip())

        min_repeat = max(3, (len(pages) + 1) // 2)
        top_counts: dict[str, int] = {}
        bottom_counts: dict[str, int] = {}
        for page in pages:
            lines = [l for l in str(page["cleaned_text"]).split("\n") if l.strip()]
            if not lines:
                continue
            for counts, edge in ((top_counts, lines[0]), (bottom_counts, lines[-1])):
                if len(edge) <= 120 and not edge.startswith("|") and not HEADING_LINE_RE.match(edge):
                    counts[_sig(edge)] = counts.get(_sig(edge), 0) + 1

        rep_tops = {s for s, c in top_counts.items() if c >= min_repeat}
        rep_bottoms = {s for s, c in bottom_counts.items() if c >= min_repeat}
        if not rep_tops and not rep_bottoms:
            return pages

        for page in pages:
            raw_lines = str(page["cleaned_text"]).split("\n")
            non_empty = [i for i, l in enumerate(raw_lines) if l.strip()]
            if not non_empty:
                continue
            drops = {
                i
                for i, sigs in ((non_empty[0], rep_tops), (non_empty[-1], rep_bottoms))
                if _sig(raw_lines[i]) in sigs
            }
            if drops:
                page["removed_noise"].extend(raw_lines[i].strip() for i in sorted(drops))
                updated = "\n".join(l for i, l in enumerate(raw_lines) if i not in drops).strip()
                page["cleaned_text"] = updated
                page["char_count"] = len(updated)
        return pages

    @classmethod
    def clean_pages(cls, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean extracted page dicts and strip repeated cross-page headers/footers."""
        cleaned_results = []
        for p in pages:
            raw_text = str(p.get("text", ""))
            cleaned_text, noise = cls.clean_page_text(raw_text)
            cleaned_results.append({
                "page_number": int(p.get("page_number", 1)),
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "char_count": len(cleaned_text),
                "removed_noise": noise,
            })
        return cls._strip_repeated_headers_footers(cleaned_results)
