import logging
from api.services.crawler.core.fetcher import HttpFetcher
from api.services.crawler.discovery.listing_extractor import ListingExtractor
from api.services.crawler.discovery.rss_parser import RssParser
from api.services.crawler.discovery.schemas import DiscoveredItem, DiscoveryResult
from api.services.crawler.discovery.sitemap_parser import SitemapParser
from api.services.crawler.discovery.url_normalizer import UrlNormalizer

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """Orchestrates candidate article discovery from listing pages, sitemaps, and feeds."""

    def __init__(
        self,
        fetcher: HttpFetcher | None = None,
        normalizer: UrlNormalizer | None = None,
        check_dns: bool = True,
    ):
        self.fetcher = fetcher or HttpFetcher(check_dns=check_dns)
        self.normalizer = normalizer or UrlNormalizer()

    async def discover(self, url: str, max_items: int = 50) -> DiscoveryResult:
        """Fetch given listing or feed URL, detect format, and extract article candidates."""
        logger.info(f"Starting discovery on: {url} (max_items={max_items})")

        response = await self.fetcher.fetch_html(url)
        text = response.html.strip()

        items: list[DiscoveredItem] = []
        lower_text = text.lower()
        source_type = "html"

        if "<urlset" in lower_text or "<sitemapindex" in lower_text:
            logger.debug(f"Parsing {url} as XML Sitemap")
            source_type = "sitemap"
            items = SitemapParser.parse(text, base_url=response.final_url, normalizer=self.normalizer)
        elif "<rss" in lower_text or "<feed" in lower_text:
            logger.debug(f"Parsing {url} as RSS/Atom Feed")
            source_type = "rss"
            items = RssParser.parse(text, base_url=response.final_url, normalizer=self.normalizer)
        else:
            logger.debug(f"Parsing {url} as HTML Listing Page")
            source_type = "html"
            items = ListingExtractor.extract_items(text, base_url=response.final_url, normalizer=self.normalizer)

        if max_items > 0:
            items = items[:max_items]

        result = DiscoveryResult(
            source_url=url,
            source_type=source_type,
            total_discovered=len(items),
            items=items,
        )
        logger.info(f"Discovery completed for {url}: found {len(items)} items")
        return result

    async def aclose(self) -> None:
        """Close underlying HTTP client."""
        await self.fetcher.aclose()
