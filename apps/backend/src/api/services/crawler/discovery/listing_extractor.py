import re
from bs4 import BeautifulSoup, Tag
from api.services.crawler.discovery.schemas import DiscoveredItem
from api.services.crawler.discovery.url_normalizer import UrlNormalizer


class ListingExtractor:
    """Heuristic extractor to discover article links, titles, dates and summaries from category pages."""

    DATE_RE = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})")
    PAGINATION_RE = re.compile(r"[?&](page|trang|p)=\d+|/page/\d+", re.IGNORECASE)

    CARD_SELECTORS = [
        "article",
        ".post-item",
        ".news-item",
        ".item-news",
        ".post",
        ".card",
        ".news-card",
        ".list-news-item",
        ".news-list-item",
        ".ts-grid-box",
        ".item",
    ]

    NOISE_CONTAINERS = [
        "nav",
        "header",
        "footer",
        ".pagination",
        ".paging",
        ".breadcrumb",
        ".sidebar",
        ".widget",
        ".menu",
        ".footer-area",
        ".header-area",
    ]

    @classmethod
    def _is_pagination_link(cls, href: str) -> bool:
        """Check if link is just a pagination or category filter URL."""
        if cls.PAGINATION_RE.search(href):
            return True
        return False

    @classmethod
    def extract_items(
        cls,
        html: str,
        base_url: str,
        normalizer: UrlNormalizer | None = None,
    ) -> list[DiscoveredItem]:
        """Scan HTML listing and extract candidate articles."""
        norm = normalizer or UrlNormalizer()
        soup = BeautifulSoup(html, "lxml")

        # 1. Decompose site-wide noise
        for selector in cls.NOISE_CONTAINERS:
            for el in soup.select(selector):
                el.decompose()

        discovered: list[DiscoveredItem] = []
        seen_urls: set[str] = set()

        # 2. Try structured card extraction first
        found_cards: list[Tag] = []
        for selector in cls.CARD_SELECTORS:
            cards = soup.select(selector)
            if len(cards) >= 2:  # Strong signal of a recurring list of posts
                found_cards = cards
                break

        if found_cards:
            for card in found_cards:
                # Find link
                a_tag = card.find("a", href=True)
                if not a_tag:
                    continue

                href = a_tag["href"].strip()
                if cls._is_pagination_link(href):
                    continue

                canonical_url = norm.normalize(href, base_url=base_url)
                if not canonical_url or canonical_url in seen_urls:
                    continue

                # Don't add listing URL itself
                if canonical_url.rstrip("/") == base_url.rstrip("/"):
                    continue

                # Title
                title = a_tag.get_text(strip=True) or a_tag.get("title", "")
                if not title:
                    h_tag = card.find(["h2", "h3", "h4"])
                    if h_tag:
                        title = h_tag.get_text(strip=True)

                if not title:
                    continue

                # Date
                published_at = None
                card_text = card.get_text()
                date_match = cls.DATE_RE.search(card_text)
                if date_match:
                    published_at = date_match.group(1)

                # Summary
                summary = None
                summary_el = card.find(class_=re.compile(r"(summary|desc|sapo|lead)", re.I)) or card.find("p")
                if summary_el:
                    summary = summary_el.get_text(strip=True)

                # Thumbnail
                thumb_url = None
                img = card.find("img", src=True)
                if img:
                    raw_src = img["src"].strip()
                    if not raw_src.startswith("data:"):
                        thumb_url = norm.normalize(raw_src, base_url=base_url)

                seen_urls.add(canonical_url)
                discovered.append(
                    DiscoveredItem(
                        url=canonical_url,
                        title=title,
                        published_at=published_at,
                        summary=summary,
                        thumbnail_url=thumb_url,
                        status="discovered",
                    )
                )

        # 3. Fallback: inspect any h2/h3/h4 links or table rows if cards yielded few results
        if len(discovered) < 2:
            for h_tag in soup.find_all(["h2", "h3", "h4"]):
                a_tag = h_tag.find("a", href=True)
                if not a_tag:
                    continue

                href = a_tag["href"].strip()
                if cls._is_pagination_link(href):
                    continue

                canonical_url = norm.normalize(href, base_url=base_url)
                if not canonical_url or canonical_url in seen_urls:
                    continue

                if canonical_url.rstrip("/") == base_url.rstrip("/"):
                    continue

                title = a_tag.get_text(strip=True) or h_tag.get_text(strip=True)
                if not title or len(title) < 5:
                    continue

                # Check parent or siblings for date
                published_at = None
                parent_text = h_tag.parent.get_text() if h_tag.parent else ""
                date_match = cls.DATE_RE.search(parent_text)
                if date_match:
                    published_at = date_match.group(1)

                seen_urls.add(canonical_url)
                discovered.append(
                    DiscoveredItem(
                        url=canonical_url,
                        title=title,
                        published_at=published_at,
                        status="discovered",
                    )
                )

        return discovered
