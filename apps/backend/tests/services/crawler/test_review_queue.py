import tempfile
import unittest
from pathlib import Path

from api.services.crawler.discovery.schemas import DiscoveredItem, DiscoveryResult
from api.services.crawler.registry.review_queue import ReviewQueueManager


class TestReviewQueue(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.queue_mgr = ReviewQueueManager(queue_dir=Path(self.temp_dir.name))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_approve_items(self):
        result = DiscoveryResult(
            source_url="https://ctsv.huce.edu.vn/danh-muc",
            total_discovered=2,
            items=[
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-1", title="TB 1"),
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-2", title="TB 2"),
            ],
            discovered_at="2026-11-10T12:00:00Z",
        )
        saved_file = self.queue_mgr.save_discovered(result)
        self.assertTrue(saved_file.exists())

        # Approve item 1 only
        approved_file = self.queue_mgr.approve_items(
            discovered_file=saved_file,
            approved_urls=["https://ctsv.huce.edu.vn/tb-1"],
        )
        self.assertTrue(approved_file.exists())
        approved_urls = self.queue_mgr.load_approved_urls(approved_file)
        self.assertEqual(approved_urls, ["https://ctsv.huce.edu.vn/tb-1"])

    def test_approve_all_items(self):
        result = DiscoveryResult(
            source_url="https://ctsv.huce.edu.vn/danh-muc",
            total_discovered=2,
            items=[
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-1", title="TB 1"),
                DiscoveredItem(url="https://ctsv.huce.edu.vn/tb-2", title="TB 2"),
            ],
            discovered_at="2026-11-10T12:00:00Z",
        )
        saved_file = self.queue_mgr.save_discovered(result)
        approved_file = self.queue_mgr.approve_items(
            discovered_file=saved_file,
            approve_all=True,
        )
        approved_urls = self.queue_mgr.load_approved_urls(approved_file)
        self.assertEqual(len(approved_urls), 2)
        self.assertIn("https://ctsv.huce.edu.vn/tb-1", approved_urls)
        self.assertIn("https://ctsv.huce.edu.vn/tb-2", approved_urls)
