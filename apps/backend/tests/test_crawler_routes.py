import unittest
from unittest.mock import MagicMock
from api.schemas.crawler import StartQueueRequest, StartQueueResponse
from api.services.crawler.task_manager import CrawlTaskManager
from api.v1.routes.crawler import router


class TestCrawlerRoutes(unittest.TestCase):
    def test_routes_registered_on_router(self):
        registered_routes = {}
        for r in router.routes:
            if hasattr(r, "path") and hasattr(r, "methods"):
                for m in r.methods:
                    registered_routes[(m, r.path)] = getattr(r, "status_code", None)

        # Verify POST /queue/start is HTTP 202
        self.assertIn(("POST", "/queue/start"), registered_routes)
        self.assertEqual(registered_routes[("POST", "/queue/start")], 202)

        # Verify POST /sessions/{session_id}/cancel is HTTP 200
        self.assertIn(("POST", "/sessions/{session_id}/cancel"), registered_routes)
        self.assertEqual(registered_routes[("POST", "/sessions/{session_id}/cancel")], 200)

        # Verify GET /sessions is HTTP 200
        self.assertIn(("GET", "/sessions"), registered_routes)
        self.assertEqual(registered_routes[("GET", "/sessions")], 200)

        # Verify GET /sessions/{session_id} is HTTP 200
        self.assertIn(("GET", "/sessions/{session_id}"), registered_routes)
        self.assertEqual(registered_routes[("GET", "/sessions/{session_id}")], 200)

    def test_start_queue_response_schema(self):
        dto = StartQueueResponse(
            session_id="batch_20261123_120000",
            status="in_progress",
            total_urls=10,
        )
        data = dto.model_dump()
        self.assertEqual(data["session_id"], "batch_20261123_120000")
        self.assertEqual(data["status"], "in_progress")
        self.assertEqual(data["total_urls"], 10)
        self.assertIn("message", data)

    def test_task_manager_concurrency_guard(self):
        manager = CrawlTaskManager()
        mock_task = MagicMock()
        mock_task.done.return_value = False

        manager.register("sess_active", mock_task)
        self.assertEqual(manager.get_active_session_id(), "sess_active")
        self.assertTrue(manager.is_active("sess_active"))

        # Cancellation
        self.assertTrue(manager.cancel("sess_active"))
        mock_task.cancel.assert_called_once()


if __name__ == "__main__":
    unittest.main()
