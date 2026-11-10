from bs4 import BeautifulSoup
from api.services.crawler.discovery.schemas import DiscoveredItem
from api.services.crawler.discovery.url_normalizer import UrlNormalizer


class SitemapParser:
    """Extracts article URLs from XML sitemaps (<urlset>)."""

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

        for url_node in soup.find_all("url"):
            loc_node = url_node.find("loc")
            if not loc_node:
                continue

            raw_url = loc_node.get_text(strip=True)
            canonical_url = norm.normalize(raw_url, base_url=base_url)
            if not canonical_url or canonical_url in seen_urls:
                continue

            lastmod_node = url_node.find("lastmod")
            published_at = lastmod_node.get_text(strip=True) if lastmod_node else None

            # Fallback title from last URL path segment
            slug = canonical_url.rstrip("/").split("/")[-1]
            title = slug.replace("-", " ").capitalize() if slug else canonical_url

            seen_urls.add(canonical_url)
            items.append(
                DiscoveredItem(
                    url=canonical_url,
                    title=title,
                    published_at=published_at,
                    status="discovered",
                )
            )

        return items
