import unittest
from unittest.mock import MagicMock
from api.services.crawler.task_manager import CrawlTaskManager

class TestCrawlTaskManager(unittest.TestCase):
    def test_register_and_cancel_task(self):
        manager = CrawlTaskManager()
        mock_task = MagicMock()
        mock_task.done.return_value = False

        manager.register("sess_123", mock_task)
        self.assertTrue(manager.is_active("sess_123"))
        self.assertEqual(manager.get_active_session_id(), "sess_123")

        # Cancel active task
        self.assertTrue(manager.cancel("sess_123"))
        mock_task.cancel.assert_called_once()

        # Task marks as done
        mock_task.done.return_value = True
        self.assertFalse(manager.is_active("sess_123"))

    def test_cancel_non_existent(self):
        manager = CrawlTaskManager()
        self.assertFalse(manager.cancel("unknown_sess"))
        self.assertIsNone(manager.get_active_session_id())

if __name__ == "__main__":
    unittest.main()
