import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.core.fetcher import FetchResponse


class TestBatchCrawl(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.engine = CrawlerCoreEngine(base_data_dir=Path(self.temp_dir.name), check_dns=False)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("api.services.crawler.core.fetcher.HttpFetcher.fetch_html", new_callable=AsyncMock)
    async def test_batch_crawl_multiple_urls(self, mock_fetch):
        mock_html = """
        <html>
            <head><title>Trang thông báo</title></head>
            <body>
                <main class="post-content">
                    <h1>Thông báo xét học bổng</h1>
                    <p>Nội dung chi tiết về học bổng kỳ 1 năm học 2026...</p>
                </main>
            </body>
        </html>
        """
        mock_fetch.return_value = FetchResponse(
            status_code=200,
            html=mock_html,
            final_url="https://ctsv.huce.edu.vn/tb",
        )

        urls = [
            "https://ctsv.huce.edu.vn/item-1",
            "https://ctsv.huce.edu.vn/item-2",
        ]
        batch_res = await self.engine.crawl_batch(urls, max_concurrency=2, skip_media=True)
        self.assertEqual(batch_res.total_urls, 2)
        self.assertEqual(batch_res.successful, 2)
        self.assertEqual(batch_res.failed, 0)
        self.assertEqual(len(batch_res.results), 2)

        session_dir = Path(self.temp_dir.name) / "sessions" / batch_res.session_id
        self.assertTrue((session_dir / "session.json").exists())
        self.assertTrue((session_dir / "results.json").exists())
