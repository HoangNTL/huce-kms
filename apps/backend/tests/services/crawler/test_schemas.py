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

    def test_crawl_result_field_mapping(self):
        result = CrawlResult(
            url="https://ctsv.huce.edu.vn/tb-1",
            status="success",
            title="Thông báo sinh viên",
            artifact_dir=settings.CRAWLER_DATA_DIR,
            pdf_count=2,
            image_count=1,
            errors=[],
        )
        # Verify status is str and does not have .value
        self.assertIsInstance(result.status, str)
        self.assertEqual(getattr(result.status, "value", str(result.status)), "success")
        self.assertEqual(result.title, "Thông báo sinh viên")
        self.assertEqual(result.pdf_count + result.image_count, 3)

    def test_discovery_result_source_type(self):
        from api.services.crawler.discovery.schemas import DiscoveryResult, DiscoveredItem
        res = DiscoveryResult(
            source_url="https://ctsv.huce.edu.vn",
            source_type="html",
            total_discovered=1,
            items=[DiscoveredItem(url="https://ctsv.huce.edu.vn/1", title="Tin 1")],
        )
        self.assertEqual(res.source_type, "html")
        self.assertEqual(getattr(res.source_type, "value", str(res.source_type)), "html")
