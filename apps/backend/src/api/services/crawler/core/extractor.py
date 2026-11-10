import re
from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ExtractedMeta:
    """Metadata extracted from HTML document head and body."""

    title: str
    published_at: str | None = None


class HtmlExtractor:
    """Extracts article title, publication date, and basic metadata from raw HTML."""

    COMMON_TITLE_SUFFIXES = [
        re.compile(r"\s*[-|–—]\s*(?:Trường\s+)?Đại\s+học\s+Xây\s+dựng(?:\s+Hà\s+Nội)?.*$", re.IGNORECASE),
        re.compile(r"\s*[-|–—]\s*HUCE.*$", re.IGNORECASE),
        re.compile(r"\s*[-|–—]\s*Cổng\s+thông\s+tin.*$", re.IGNORECASE),
    ]

    DATE_PATTERNS = [
        re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)"),
        re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
    ]

    @classmethod
    def _clean_title(cls, title: str) -> str:
        """Strip site branding suffixes from page title."""
        cleaned = title.strip()
        for suffix_re in cls.COMMON_TITLE_SUFFIXES:
            cleaned = suffix_re.sub("", cleaned).strip()
        return cleaned or title.strip()

    @classmethod
    def extract_metadata(cls, html: str, url: str) -> ExtractedMeta:
        """Extract title and publication date from HTML."""
        soup = BeautifulSoup(html, "lxml")

        # 1. Title extraction
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = cls._clean_title(str(og_title["content"]))

        if not title:
            h1 = soup.find("h1")
            if h1:
                title = cls._clean_title(h1.get_text(strip=True))

        if not title and soup.title:
            title = cls._clean_title(soup.title.get_text(strip=True))

        if not title:
            title = "Tài liệu không có tiêu đề"

        # 2. Publication date extraction
        published_at = None
        pub_meta = (
            soup.find("meta", property="article:published_time")
            or soup.find("meta", property="og:published_time")
            or soup.find("meta", attrs={"name": "pubdate"})
            or soup.find("meta", attrs={"name": "date"})
            or soup.find("meta", attrs={"name": "dc.date"})
        )
        if pub_meta and pub_meta.get("content"):
            published_at = str(pub_meta["content"]).strip()

        if not published_at:
            time_tag = soup.find("time")
            if time_tag:
                published_at = time_tag.get("datetime") or time_tag.get_text(strip=True)

        if not published_at:
            # Check for date pattern in date classes or post metadata
            date_elem = soup.find(class_=re.compile(r"(date|post-date|publish-date|entry-date|meta-date)", re.I))
            if date_elem:
                text = date_elem.get_text()
                for pattern in cls.DATE_PATTERNS:
                    match = pattern.search(text)
                    if match:
                        published_at = match.group(1)
                        break

        return ExtractedMeta(title=title, published_at=published_at)
