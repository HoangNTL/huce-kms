import unittest
from api.constants.enums import CrawlSessionStatus, CrawlItemStatus

class TestCrawlSessionModels(unittest.TestCase):
    def test_crawl_session_status_values(self):
        self.assertEqual(CrawlSessionStatus.PENDING, 0)
        self.assertEqual(CrawlSessionStatus.IN_PROGRESS, 1)
        self.assertEqual(CrawlSessionStatus.COMPLETED, 2)
        self.assertEqual(CrawlSessionStatus.FAILED, 3)
        self.assertEqual(CrawlSessionStatus.CANCELLED, 4)
        self.assertEqual(CrawlSessionStatus.INTERRUPTED, 5)

    def test_crawl_session_status_helpers(self):
        self.assertEqual(CrawlSessionStatus.IN_PROGRESS.name_str, "in_progress")
        self.assertEqual(CrawlSessionStatus.INTERRUPTED.name_str, "interrupted")
        self.assertEqual(CrawlSessionStatus.from_str("in_progress"), CrawlSessionStatus.IN_PROGRESS)
        self.assertEqual(CrawlSessionStatus.from_str("cancelled"), CrawlSessionStatus.CANCELLED)
        self.assertEqual(CrawlSessionStatus.from_str("5"), CrawlSessionStatus.INTERRUPTED)

    def test_crawl_item_status_values(self):
        self.assertEqual(CrawlItemStatus.PENDING, 0)
        self.assertEqual(CrawlItemStatus.RUNNING, 1)
        self.assertEqual(CrawlItemStatus.SUCCESS, 2)
        self.assertEqual(CrawlItemStatus.PARTIAL, 3)
        self.assertEqual(CrawlItemStatus.FAILED, 4)
        self.assertEqual(CrawlItemStatus.SKIPPED, 5)

    def test_crawl_item_status_helpers(self):
        self.assertEqual(CrawlItemStatus.SUCCESS.name_str, "success")
        self.assertEqual(CrawlItemStatus.FAILED.name_str, "failed")
        self.assertEqual(CrawlItemStatus.from_str("success"), CrawlItemStatus.SUCCESS)
        self.assertEqual(CrawlItemStatus.from_str("partial"), CrawlItemStatus.PARTIAL)
        self.assertEqual(CrawlItemStatus.from_str("5"), CrawlItemStatus.SKIPPED)

    def test_model_import(self):
        from api.models.crawl_session import CrawlSession, CrawlSessionItem
        self.assertEqual(CrawlSession.__tablename__, "crawl_sessions")
        self.assertEqual(CrawlSessionItem.__tablename__, "crawl_session_items")


if __name__ == "__main__":
    unittest.main()
