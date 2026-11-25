import re
import unicodedata
from typing import Any


class TextCleaner:
    """Pre-processing and text sanitization pipeline for Vietnamese academic documents."""

    # Regex patterns for page numbering and repeated administrative noise
    NOISE_PATTERNS = [
        re.compile(r"^\s*Trang\s+\d+(\s*[/_\\-]\s*\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*-\s*\d+\s*-\s*$"),
        re.compile(r"^\s*Page\s+\d+(\s*of\s*\d+)?\s*$", re.IGNORECASE),
        re.compile(r"^\s*\[\s*\d+\s*\]\s*$"),
    ]

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Normalize Vietnamese text to canonical pre-composed NFC Unicode."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", text)

    @classmethod
    def clean_page_text(cls, text: str) -> tuple[str, list[str]]:
        """
        Sanitize raw page text:
        1. NFC Unicode normalization.
        2. Identify and filter page noise / pagination lines.
        3. De-hyphenate broken lines and redundant whitespace.
        Returns (cleaned_text, removed_noise_list).
        """
        if not text:
            return "", []

        # 1. Normalize Unicode
        normalized = cls.normalize_unicode(text)
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        lines = normalized.split("\n")
        retained_lines: list[str] = []
        removed_noise: list[str] = []

        # Find first and last non-empty line indices to safely detect standalone page numbers (header/footer)
        non_empty_indices = [i for i, l in enumerate(lines) if l.strip()]
        header_footer_indices: set[int] = set()
        if non_empty_indices:
            first_idx = non_empty_indices[0]
            if re.match(r"^\s*\d{1,4}\s*$", lines[first_idx]):
                header_footer_indices.add(first_idx)
            last_idx = non_empty_indices[-1]
            if last_idx != first_idx and re.match(r"^\s*\d{1,4}\s*$", lines[last_idx]):
                header_footer_indices.add(last_idx)

        # 2. Filter noise line by line
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                retained_lines.append("")
                continue

            is_noise = (
                idx in header_footer_indices
                or any(pattern.match(stripped) for pattern in cls.NOISE_PATTERNS)
            )
            if is_noise:
                removed_noise.append(stripped)
            else:
                retained_lines.append(stripped)

        # 3. Rebuild text and perform de-hyphenation and whitespace cleanup
        joined = "\n".join(retained_lines)

        # Handle hyphen at end of line (e.g. "nghiên-\ncứu" -> "nghiên cứu")
        joined = re.sub(r"(\w+)-\n(\w+)", r"\1\2", joined)

        # Handle soft break: join non-empty line ending without sentence terminators
        # to a subsequent line that begins with a Unicode lowercase character.
        raw_split_lines = joined.split("\n")
        merged_lines: list[str] = []

        for line in raw_split_lines:
            stripped_line = line.strip()
            if not stripped_line:
                merged_lines.append("")
                continue

            if merged_lines and merged_lines[-1] != "":
                prev_line = merged_lines[-1]
                prev_ends_softly = prev_line[-1] not in ".!?:"
                curr_starts_lower = stripped_line[0].islower()

                if prev_ends_softly and curr_starts_lower:
                    merged_lines[-1] = f"{prev_line} {stripped_line}"
                    continue

            merged_lines.append(stripped_line)

        joined = "\n".join(merged_lines)

        # Collapse excessive blank lines (more than 2 consecutive newlines)
        joined = re.sub(r"\n{3,}", "\n\n", joined)

        # Collapse horizontal whitespace
        cleaned_lines = [re.sub(r"[ \t]+", " ", l).strip() for l in joined.split("\n")]
        final_text = "\n".join(cleaned_lines).strip()

        return final_text, removed_noise

    @classmethod
    def clean_pages(cls, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Clean a list of extracted page dictionaries.
        Each input dict should have 'page_number' and 'text'.
        Returns a structured list with 'page_number', 'raw_text', 'cleaned_text', and 'removed_noise'.
        """
        cleaned_results: list[dict[str, Any]] = []

        for p in pages:
            raw_text = str(p.get("text", ""))
            page_number = int(p.get("page_number", 1))

            cleaned_text, noise = cls.clean_page_text(raw_text)

            cleaned_results.append({
                "page_number": page_number,
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "char_count": len(cleaned_text),
                "removed_noise": noise,
            })

        return cleaned_results
