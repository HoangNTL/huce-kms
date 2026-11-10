import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from api.models.document import Document
from api.schemas.document import DocumentResponse
from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter


class TestIngestionAdapter(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

        # Setup dummy page
        self.page_dir = self.base_dir / "page_abc"
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
        (self.page_dir / "content.md").write_text("# Thông báo học bổng\n\nNội dung chi tiết...", encoding="utf-8")
        (self.page_dir / "pdfs" / "quyet_dinh.pdf").write_bytes(b"%PDF-1.4 dummy content")

        # Mock dependencies
        self.mock_doc_service = MagicMock()
        self.mock_doc_repo = MagicMock()
        self.mock_doc_repo.get_by_file_hash = AsyncMock(return_value=None)

        # When creating in draft mode
        async def fake_create(doc):
            doc.id = 101
            return doc

        self.mock_doc_repo.create = AsyncMock(side_effect=fake_create)

        self.adapter = CrawlIngestionAdapter(
            document_service=self.mock_doc_service,
            document_repo=self.mock_doc_repo,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_ingest_page_draft_mode(self):
        results = await self.adapter.ingest_page(self.page_dir, auto_publish=False)
        self.assertEqual(len(results), 2)  # 1 markdown + 1 pdf
        self.assertEqual(results[0].status, "uploaded")
        self.assertEqual(results[0].file_type, "md")
        self.assertEqual(results[1].status, "uploaded")
        self.assertEqual(results[1].file_type, "pdf")
        self.assertEqual(self.mock_doc_repo.create.call_count, 2)
        self.mock_doc_service.upload_and_process_document.assert_not_called()

    async def test_ingest_page_auto_publish_mode(self):
        now = datetime.now(timezone.utc)
        mock_resp = DocumentResponse(
            id=202,
            title="Thông báo học bổng",
            file_name="page_abc_content.md",
            file_path="/data/uploads/page_abc_content.md",
            file_type="md",
            file_size=100,
            file_hash="hash123",
            status="indexed",
            uploader_id=None,
            total_pages=1,
            chunk_count=3,
            error_message=None,
            created_at=now,
            updated_at=now,
        )
        self.mock_doc_service.upload_and_process_document = AsyncMock(return_value=mock_resp)

        results = await self.adapter.ingest_page(self.page_dir, auto_publish=True)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].status, "indexed")
        self.assertEqual(results[0].chunks_count, 3)
        self.assertEqual(self.mock_doc_service.upload_and_process_document.call_count, 2)

    async def test_ingest_duplicate_skips(self):
        # Mock that file_hash already exists
        existing_doc = MagicMock()
        existing_doc.id = 55
        self.mock_doc_repo.get_by_file_hash = AsyncMock(return_value=existing_doc)

        results = await self.adapter.ingest_page(self.page_dir, auto_publish=False)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].status, "skipped")
        self.assertEqual(results[1].status, "skipped")
        self.mock_doc_repo.create.assert_not_called()

    async def test_ingest_session(self):
        session_dir = self.base_dir / "sessions" / "sess_xyz"
        session_dir.mkdir(parents=True, exist_ok=True)
        results_data = [
            {"artifact_dir": str(self.page_dir), "status": "success", "url": "https://ctsv.huce.edu.vn/tb-1"}
        ]
        (session_dir / "results.json").write_text(json.dumps(results_data), encoding="utf-8")

        summary = await self.adapter.ingest_session(session_dir, auto_publish=False)
        self.assertEqual(summary.total_pages, 1)
        self.assertEqual(summary.total_documents, 2)
        self.assertEqual(summary.successful, 2)
        self.assertEqual(summary.failed, 0)

