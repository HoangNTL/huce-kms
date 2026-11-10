import unittest
from api.core.config import settings
from api.services.crawler.schemas import CrawlResult, PageMetadata, CrawledMediaItem
from api.services.crawler.exceptions import SSRFBlockedException


class TestCrawlerSchemas(unittest.TestCase):
    def test_settings_has_crawler_defaults(self):
        self.assertIn("huce.edu.vn", settings.CRAWLER_ALLOWED_DOMAINS)
        self.assertEqual(settings.CRAWLER_MAX_FILE_SIZE_MB, 20)
        self.assertEqual(settings.CRAWLER_REQUEST_TIMEOUT, 15)
        self.assertEqual(settings.CRAWLER_MAX_RETRIES, 2)

    def test_page_metadata_serialization(self):
        meta = PageMetadata(
            source_url="https://daotao.huce.edu.vn/thong-bao-1",
            canonical_url="https://daotao.huce.edu.vn/thong-bao-1",
            domain="daotao.huce.edu.vn",
            title="Thông báo 1",
            crawled_at="2026-11-10T10:00:00Z",
            content_hash="sha256:abc123",
            markdown_file="content.md",
        )
        data = meta.model_dump()
        self.assertEqual(data["source"]["url"], "https://daotao.huce.edu.vn/thong-bao-1")
        self.assertEqual(data["content"]["title"], "Thông báo 1")
        self.assertEqual(data["media"]["pdfs"], [])
        self.assertEqual(data["media"]["images"], [])
        self.assertEqual(data["crawl"]["status"], "success")

    def test_crawled_media_item(self):
        item = CrawledMediaItem(
            url="https://daotao.huce.edu.vn/files/qd.pdf",
            local_path="pdfs/qd.pdf",
            file_name="qd.pdf",
            file_size=1024,
            file_hash="sha256:fakehash",
            mime_type="application/pdf",
            media_type="pdf",
        )
        self.assertEqual(item.media_type, "pdf")
        self.assertEqual(item.status, "success")
