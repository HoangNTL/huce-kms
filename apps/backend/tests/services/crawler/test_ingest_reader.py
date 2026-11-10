import json
import tempfile
import unittest
from pathlib import Path

from api.services.crawler.ingestion.reader import CrawlArtifactReader


class TestIngestReader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Create dummy page
        self.page_dir = self.base_dir / "page_123"
        (self.page_dir / "pdfs").mkdir(parents=True, exist_ok=True)

        meta_data = {
            "schema_version": "1.0",
            "source": {
                "url": "https://ctsv.huce.edu.vn/tb-1",
                "canonical_url": "https://ctsv.huce.edu.vn/tb-1",
                "domain": "ctsv.huce.edu.vn",
                "type": "web",
            },
            "content": {
                "title": "Thông báo học bổng",
                "published_at": "11/11/2026",
                "crawled_at": "2026-11-11T00:00:00Z",
                "markdown_file": "content.md",
                "content_hash": "abc123hash",
            },
            "media": {"pdfs": [], "images": []},
            "crawl": {"status": "success", "http_status": 200},
        }
        (self.page_dir / "metadata.json").write_text(json.dumps(meta_data), encoding="utf-8")
        (self.page_dir / "content.md").write_text("# Thông báo học bổng\n\nChi tiết...", encoding="utf-8")
        (self.page_dir / "pdfs" / "quyet_dinh.pdf").write_bytes(b"%PDF-1.4 dummy pdf")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_read_single_page(self):
        payload = CrawlArtifactReader.read_page(self.page_dir)
        self.assertEqual(payload.metadata.content.title, "Thông báo học bổng")
        self.assertIn("# Thông báo học bổng", payload.markdown_content)
        self.assertEqual(len(payload.pdf_files), 1)
        self.assertEqual(payload.pdf_files[0].name, "quyet_dinh.pdf")

    def test_read_session(self):
        session_dir = self.base_dir / "sessions" / "sess_001"
        session_dir.mkdir(parents=True, exist_ok=True)
        results_data = [
            {"artifact_dir": str(self.page_dir), "status": "success", "url": "https://ctsv.huce.edu.vn/tb-1"}
        ]
        (session_dir / "results.json").write_text(json.dumps(results_data), encoding="utf-8")

        payloads = CrawlArtifactReader.read_session(session_dir)
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0].metadata.source.url, "https://ctsv.huce.edu.vn/tb-1")
