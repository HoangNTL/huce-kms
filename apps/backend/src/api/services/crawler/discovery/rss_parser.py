from bs4 import BeautifulSoup
from api.services.crawler.discovery.schemas import DiscoveredItem
from api.services.crawler.discovery.url_normalizer import UrlNormalizer


class RssParser:
    """Extracts article items from RSS / Atom feeds."""

    @classmethod
    def parse(
        cls,
        xml_content: str,
        base_url: str,
        normalizer: UrlNormalizer | None = None,
    ) -> list[DiscoveredItem]:
        norm = normalizer or UrlNormalizer()
        soup = BeautifulSoup(xml_content, "xml")

        items: list[DiscoveredItem] = []
        seen_urls: set[str] = set()

        entries = soup.find_all("item") or soup.find_all("entry")

        for entry in entries:
            raw_url = None
            link_node = entry.find("link")
            if link_node:
                raw_url = link_node.get("href") or link_node.get_text(strip=True)

            if not raw_url:
                continue

            canonical_url = norm.normalize(raw_url, base_url=base_url)
            if not canonical_url or canonical_url in seen_urls:
                continue

            title_node = entry.find("title")
            title = title_node.get_text(strip=True) if title_node else ""

            date_node = entry.find(["pubDate", "published", "updated"])
            published_at = date_node.get_text(strip=True) if date_node else None

            summary_node = entry.find(["description", "summary", "content"])
            summary = summary_node.get_text(strip=True) if summary_node else None

            seen_urls.add(canonical_url)
            items.append(
                DiscoveredItem(
                    url=canonical_url,
                    title=title or canonical_url,
                    published_at=published_at,
                    summary=summary,
                    status="discovered",
                )
            )

        return items
