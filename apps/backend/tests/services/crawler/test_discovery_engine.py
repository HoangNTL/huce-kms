import unittest
from unittest.mock import AsyncMock, patch
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.core.fetcher import FetchResponse


class TestDiscoveryEngine(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.engine = DiscoveryEngine(check_dns=False)

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    async def test_discover_from_listing_page(self, mock_fetch):
        mock_html = """
        <html><body>
            <div class="post-item"><h3><a href="/tb-1">Thông báo 1</a></h3></div>
            <div class="post-item"><h3><a href="/tb-2">Thông báo 2</a></h3></div>
        </body></html>
        """
        mock_fetch.return_value = FetchResponse(
            status_code=200,
            html=mock_html,
            final_url="https://ctsv.huce.edu.vn/danh-muc",
        )

        res = await self.engine.discover("https://ctsv.huce.edu.vn/danh-muc", max_items=10)
        self.assertEqual(res.source_url, "https://ctsv.huce.edu.vn/danh-muc")
        self.assertEqual(res.total_discovered, 2)
        self.assertEqual(res.items[0].url, "https://ctsv.huce.edu.vn/tb-1")

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    async def test_discover_from_sitemap(self, mock_fetch):
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://daotao.huce.edu.vn/page-1</loc></url>
            <url><loc>https://daotao.huce.edu.vn/page-2</loc></url>
            <url><loc>https://daotao.huce.edu.vn/page-3</loc></url>
        </urlset>
        """
        mock_fetch.return_value = FetchResponse(
            status_code=200,
            html=mock_xml,
            final_url="https://daotao.huce.edu.vn/sitemap.xml",
        )

        res = await self.engine.discover("https://daotao.huce.edu.vn/sitemap.xml", max_items=2)
        self.assertEqual(res.total_discovered, 2)
        self.assertEqual(res.items[0].url, "https://daotao.huce.edu.vn/page-1")
