from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock

from api.core.exceptions import BadRequestException, EntityNotFoundException
from api.schemas.document import DocumentUpdate
from api.services.document import DocumentService


class TestDocumentUpdateService(unittest.IsolatedAsyncioTestCase):
    async def test_update_document_title_and_category(self):
        doc_repo = AsyncMock()
        chunk_repo = AsyncMock()
        category_repo = AsyncMock()
        embedder = AsyncMock()
        vector_store = AsyncMock()

        now = datetime.now(timezone.utc)
        mock_category = MagicMock()
        mock_category.id = 2
        mock_category.name = "New Category"
        mock_category.slug = "new-cat"
        mock_category.description = "Desc"
        mock_category.created_at = now
        mock_category.updated_at = now
        mock_doc = MagicMock(
            id=1,
            title="Old Title",
            category_id=1,
            file_name="test.pdf",
            file_path="uploads/test.pdf",
            file_size=1024,
            file_type="pdf",
            file_hash="hash123",
            status="indexed",
            uploader_id=1,
            total_pages=1,
            chunk_count=2,
            error_message=None,
            created_at=now,
            updated_at=now,
            category=mock_category,
        )
        doc_repo.get_by_id.return_value = mock_doc
        category_repo.get_by_id.return_value = mock_category
        doc_repo.update.return_value = mock_doc
        doc_repo.get_with_category.return_value = mock_doc

        service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store)
        res = await service.update_document(1, DocumentUpdate(title="New Title", category_id=2))

        self.assertEqual(mock_doc.title, "New Title")
        self.assertEqual(mock_doc.category_id, 2)
        self.assertEqual(res.title, "New Title")
        vector_store.update_payload_by_document_id.assert_awaited_once_with(
            document_id=1,
            payload={"category_id": 2, "title": "New Title"},
        )

    async def test_update_document_unassign_category(self):
        doc_repo = AsyncMock()
        chunk_repo = AsyncMock()
        category_repo = AsyncMock()
        embedder = AsyncMock()
        vector_store = AsyncMock()

        now = datetime.now(timezone.utc)
        mock_doc = MagicMock(
            id=1,
            title="Current Title",
            category_id=5,
            file_name="test.pdf",
            file_path="uploads/test.pdf",
            file_size=1024,
            file_type="pdf",
            file_hash="hash123",
            status="indexed",
            uploader_id=1,
            total_pages=1,
            chunk_count=2,
            error_message=None,
            created_at=now,
            updated_at=now,
            category=None,
        )
        doc_repo.get_by_id.return_value = mock_doc
        doc_repo.update.return_value = mock_doc
        doc_repo.get_with_category.return_value = mock_doc

        service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store)
        res = await service.update_document(1, DocumentUpdate(category_id=None))

        self.assertIsNone(mock_doc.category_id)
        category_repo.get_by_id.assert_not_called()
        vector_store.update_payload_by_document_id.assert_awaited_once_with(
            document_id=1,
            payload={"category_id": None},
        )

    async def test_update_document_not_found_raises(self):
        doc_repo = AsyncMock()
        chunk_repo = AsyncMock()
        category_repo = AsyncMock()
        embedder = AsyncMock()
        vector_store = AsyncMock()

        doc_repo.get_by_id.return_value = None
        service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store)

        with self.assertRaises(EntityNotFoundException):
            await service.update_document(999, DocumentUpdate(title="Non-existent"))

    async def test_update_invalid_category_raises(self):
        doc_repo = AsyncMock()
        chunk_repo = AsyncMock()
        category_repo = AsyncMock()
        embedder = AsyncMock()
        vector_store = AsyncMock()

        mock_doc = MagicMock(id=1, title="Valid Doc", category_id=1)
        doc_repo.get_by_id.return_value = mock_doc
        category_repo.get_by_id.return_value = None  # Category not found!

        service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store)
        with self.assertRaises(EntityNotFoundException):
            await service.update_document(1, DocumentUpdate(category_id=999))


if __name__ == "__main__":
    unittest.main()
