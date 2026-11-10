import json
from pathlib import Path
import tempfile
import unittest

from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.schemas import PageMetadata
from api.services.crawler.storage.artifact_storage import ArtifactStorage


class TestArtifactStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = ArtifactStorage(base_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_url_hash_consistency(self):
        url = "https://ctsv.huce.edu.vn/thong-bao-1"
        h1 = Deduplicator.hash_url(url)
        h2 = Deduplicator.hash_url(url + "/")  # Trailing slash normalization
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)

    def test_save_page_artifacts(self):
        meta = PageMetadata(
            source_url="https://ctsv.huce.edu.vn/tb-1",
            canonical_url="https://ctsv.huce.edu.vn/tb-1",
            domain="ctsv.huce.edu.vn",
            title="Thông báo 1",
            crawled_at="2026-11-10T10:00:00Z",
            content_hash="sha256:12345",
            markdown_file="content.md",
        )
        page_dir = self.storage.save_page(
            url="https://ctsv.huce.edu.vn/tb-1",
            metadata=meta,
            raw_html="<html><body>test</body></html>",
            markdown_content="# Thông báo 1\nTest",
        )
        self.assertTrue((page_dir / "content.md").exists())
        self.assertTrue((page_dir / "metadata.json").exists())
        self.assertTrue((page_dir / "raw.html").exists())
        self.assertTrue((page_dir / "pdfs").exists())
        self.assertTrue((page_dir / "images").exists())

        # Verify metadata content
        with open(page_dir / "metadata.json", "r", encoding="utf-8") as f:
            saved_json = json.load(f)
        self.assertEqual(saved_json["source"]["url"], "https://ctsv.huce.edu.vn/tb-1")
        self.assertEqual(saved_json["content"]["title"], "Thông báo 1")
