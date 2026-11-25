"""Shared structural & heading regex patterns for Vietnamese/English academic documents."""

import re

CHAPTER_PATTERN = re.compile(
    r"^(?:CHƯƠNG|Chương)\s+([IVXLCDM\d]+)(?:\s*[:.\-]\s*(.*))?$", re.MULTILINE
)
SECTION_PATTERN = re.compile(
    r"^(?:MỤC|Mục)\s+(\d+)(?:\s*[:.\-]\s*(.*))?$", re.MULTILINE
)
ARTICLE_PATTERN = re.compile(
    r"^(?:ĐIỀU|Điều)\s+(\d+)(?:\s*[:.\-]\s*(.*))?$", re.MULTILINE
)
APPENDIX_PATTERN = re.compile(
    r"^(PHỤ LỤC|Phụ lục|APPENDIX|Appendix)\s+([IVXLCDM\d]+)(?:\s*[:.\-]\s*(.*))?$",
    re.MULTILINE,
)
REGULATION_START_PATTERN = re.compile(
    r"^QUY\s+CHẾ(?:\s+[A-ZÀ-Ỹ0-9\s,.\-()]+)?$"
)
ATTACHED_FORM_PATTERN = re.compile(
    r"^(?:PHIẾU|MẪU|BIỂU\s+MẪU|BẢNG\s+(?:ĐÁNH\s+GIÁ|TỔNG\s+HỢP|THEO\s+DÕI|KÊ\s+KHAI))\s+[A-ZÀ-ỸĐ0-9\s,.\-()]{6,}$"
)
ATTACHMENT_META_PATTERN = re.compile(
    r"^\((?:Kèm theo|Ban hành kèm theo|Issued under|Attached to)\s+(?:Quyết định|Decision)\b",
    re.IGNORECASE,
)
TABLE_CAPTION_PATTERN = re.compile(
    r"^(?:Ma trận\b|Bảng\b|Correlation between\b|Table\s+\d*\b)",
    re.IGNORECASE,
)

CLAUSE_OR_LIST_PATTERN = re.compile(r"^(?:\d+(?:\.\d+)*\.\s|[a-z]\)\s|[-•*–]\s|\|)")
CLAUSE_NO_PATTERN = re.compile(r"^(\d+)\.\s", re.MULTILINE)
SUB_ITEM_BREAK_PATTERN = re.compile(r"^(?:\d+(?:\.\d+)*\.\s|[a-z]\)\s|(?:UGA|ULO)\d+\s*[:.])")

# Shared cleaner patterns to prevent merging structural headings/list items on soft breaks
STRUCTURAL_LINE_RE = re.compile(
    r"^(?:[-•*–]\s+|\d+(?:\.\d+)*[.)]\s+|[a-z]\)\s+|[IVXLCDM]+\.\s+|"
    r"(?:UGA|ULO|TC)\d*\b|"
    r"(?:CHƯƠNG|Chương|MỤC|Mục|ĐIỀU|Điều|PHỤ LỤC|Phụ lục|APPENDIX|Appendix|"
    r"Criterion|Tiêu chuẩn|Nơi nhận)\b)"
)
HEADING_LINE_RE = re.compile(
    r"^(?:CHƯƠNG|Chương|MỤC|Mục|ĐIỀU|Điều|PHỤ LỤC|Phụ lục|APPENDIX|Appendix)\b|"
    r"^\d+(?:\.\d+)*\.\s+[^\n]{1,120}$"
)


def strip_markdown_markers(line: str) -> str:
    """Strip Markdown heading (#) and emphasis (**, __, `) markers for structural matching."""
    cleaned = re.sub(r"^#{1,6}\s*", "", line.strip())
    return re.sub(r"[*_`]+", "", cleaned).strip()


VN_ACCENTED_LOWER = (
    "àáảãạăằắẳẵặâầấẩẫậ"
    "èéẻẽẹêềếểễệ"
    "ìíỉĩị"
    "òóỏõọôồốổỗộơờớởỡợ"
    "ùúủũụưừứửữự"
    "ỳýỷỹỵ"
)
VN_ACCENTED_ALL = f"{VN_ACCENTED_LOWER}{VN_ACCENTED_LOWER.upper()}đĐ"
_VN_DIACRITIC_CHAR_RE = re.compile(rf"[{VN_ACCENTED_ALL}]")
BULLET_OR_ITEM_RE = re.compile(r"^(?:[-•*–]\s+|\d+[.)]\s+|[a-z]\)\s+)")
BARE_PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,4}\s*$")
REPEATED_COMMA_RE = re.compile(r"(?:\s*,\s*){2,}")
# Collapse form fill-in dotted blanks (e.g. "……", "......", "……….…..") while keeping single "…" or "..."
FORM_BLANK_RE = re.compile(r"(?:…{2,}|(?<!\.)\.{4,})[….]*(?:[ \t]+(?:…{2,}|(?<!\.)\.{3,})[….]*)*")
_PUA_BULLET_TRANSLATION = str.maketrans({
    "\uf02b": "-",  # Symbol font '+' bullet
    "\uf02d": "-",  # Symbol font '-' bullet
    "\uf0a7": "-",  # Wingdings square bullet
    "\uf0a8": "-",  # Wingdings hollow square bullet
    "\uf0b7": "-",  # Symbol font round bullet
    "\uf076": "-",  # Wingdings diamond bullet
    "\uf0be": "-",  # Symbol horizontal bar
    "\uf0d8": "-",  # Wingdings arrow bullet
    "\uf0fc": "-",  # Wingdings checkmark bullet
    "\uf0fe": "-",  # Wingdings checked box bullet
})


def sanitize_pdf_symbols(text: str) -> str:
    """Normalize zero-width chars, translate Wingdings/Symbol PUA bullets, and strip unknown PUA glyphs."""
    if not text:
        return ""
    cleaned = re.sub(r"[\u200b-\u200d\ufeff\u00ad]", "", text).translate(_PUA_BULLET_TRANSLATION)
    return re.sub(r"[\ue000-\uf8ff]", "", cleaned)

CEREMONIAL_BOILERPLATE_PATTERNS = (
    re.compile(r"^\s*CỘNG\s+HÒA\s+XÃ\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM\s*$", re.IGNORECASE),
    re.compile(r"^\s*Độc\s+lập\s*[–\-—]+\s*Tự\s+do\s*[–\-—]+\s*Hạnh\s+phúc\s*$", re.IGNORECASE),
)
DOC_NUMBER_RE = re.compile(
    r"\bSố\s*(?::\s*([A-Za-z0-9À-Ỹ\-_/]+(?:\s*/\s*[A-Za-z0-9À-Ỹ\-_/]+)?)|\s+(\d+\s*/\s*[A-Za-z0-9À-Ỹ\-_/]+))",
    re.IGNORECASE,
)
ISSUED_DATE_RE = re.compile(
    r"ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})\s+năm\s+(\d{4})", re.IGNORECASE
)


def detect_language(text: str) -> str | None:
    """Detect primary language ('vi' or 'en') using Vietnamese diacritic density; None if indeterminate."""
    if not text or not text.strip():
        return None
    vn_chars = len(_VN_DIACRITIC_CHAR_RE.findall(text))
    ascii_letters = sum(1 for ch in text if ("a" <= ch <= "z") or ("A" <= ch <= "Z"))
    total_alpha = vn_chars + ascii_letters
    if total_alpha == 0:
        return None
    # Require >= 8% diacritic density on longer passages so English chunks quoting a Vietnamese title stay 'en'
    if vn_chars >= 2 and (total_alpha < 80 or (vn_chars / total_alpha) >= 0.08):
        return "vi"
    if ascii_letters >= 6:
        return "en"
    return None
