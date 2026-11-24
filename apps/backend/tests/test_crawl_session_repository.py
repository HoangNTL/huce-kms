import unittest
from api.constants.enums import CrawlSessionStatus, CrawlItemStatus

class TestCrawlSessionRepositoryInterface(unittest.TestCase):
    def test_repo_has_methods(self):
        from api.repositories.crawl_session import CrawlSessionRepository
        self.assertTrue(hasattr(CrawlSessionRepository, "create_session"))
        self.assertTrue(hasattr(CrawlSessionRepository, "increment_progress"))
        self.assertTrue(hasattr(CrawlSessionRepository, "save_item_result"))
        self.assertTrue(hasattr(CrawlSessionRepository, "complete_session"))
        self.assertTrue(hasattr(CrawlSessionRepository, "get_active_session"))
        self.assertTrue(hasattr(CrawlSessionRepository, "get_by_session_id_str"))
        self.assertTrue(hasattr(CrawlSessionRepository, "list_sessions"))
        self.assertTrue(hasattr(CrawlSessionRepository, "recover_interrupted_sessions"))


if __name__ == "__main__":
    unittest.main()
