import re
from dataclasses import dataclass
from bs4 import BeautifulSoup, Tag
import trafilatura


@dataclass
class CleanedHtmlResult:
    """Output of HTML boilerplate cleaning and main content isolation."""

    main_content_html: str
    soup: BeautifulSoup


class HtmlCleaner:
    """Removes headers, footers, sidebars, navigation, ads and isolates main article content."""

    NOISE_TAGS = [
        "script",
        "style",
        "noscript",
        "header",
        "nav",
        "footer",
        "aside",
        "iframe",
        "form",
        "button",
        "svg",
    ]

    NOISE_SELECTORS = [
        ".sidebar",
        ".widget",
        ".menu",
        ".nav",
        ".navigation",
        ".footer",
        ".header",
        ".social",
        ".share",
        ".banner",
        ".ads",
        ".advertisement",
        ".breadcrumb",
        ".comments",
        "#comments",
        ".related-posts",
        ".related-news",
    ]

    CONTENT_CANDIDATE_SELECTORS = [
        "main",
        "article",
        ".entry-content",
        ".post-content",
        ".article-content",
        ".content-detail",
        ".detail-content",
        "#main-content",
        "#content",
        ".main-content",
    ]

    @classmethod
    def clean_and_isolate_content(cls, html: str, url: str) -> CleanedHtmlResult:
        """Strip boilerplate and return isolated main content DOM."""
        soup = BeautifulSoup(html, "lxml")

        # 1. Remove explicit noise tags
        for tag_name in cls.NOISE_TAGS:
            for elem in soup.find_all(tag_name):
                elem.decompose()

        # 2. Remove noise by selectors
        for selector in cls.NOISE_SELECTORS:
            for elem in soup.select(selector):
                elem.decompose()

        # 3. Locate primary article container
        content_element: Tag | None = None
        for selector in cls.CONTENT_CANDIDATE_SELECTORS:
            found = soup.select_one(selector)
            if found:
                content_element = found
                break

        if not content_element:
            content_element = soup.body or soup

        # Clean any remaining empty divs/spans
        cleaned_html = str(content_element)
        isolated_soup = BeautifulSoup(cleaned_html, "lxml")

        return CleanedHtmlResult(
            main_content_html=cleaned_html,
            soup=isolated_soup,
        )
