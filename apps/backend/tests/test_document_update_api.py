import asyncio
from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from api.core.exceptions import BadRequestException, EntityNotFoundException
from api.schemas.document import DocumentUpdate
from api.services.document import DocumentService


class TestDocumentUpdateService(unittest.TestCase):
    def test_update_document_title_and_category(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            now = datetime.now(timezone.utc)
            doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
            cat_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef2")
            user_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef1")

            mock_category = MagicMock()
            mock_category.id = cat_id
            mock_category.name = "New Category"
            mock_category.slug = "new-cat"
            mock_category.description = "Desc"
            mock_category.created_at = now
            mock_category.updated_at = now
            mock_doc = MagicMock(
                id=doc_id,
                title="Old Title",
                category_id=None,
                file_name="test.pdf",
                file_path="uploads/test.pdf",
                file_size=1024,
                file_type="pdf",
                file_hash="hash123",
                status="indexed",
                created_by_id=user_id,
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

            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())
            res = await service.update_document(doc_id, DocumentUpdate(title="New Title", category_id=cat_id))

            self.assertEqual(mock_doc.title, "New Title")
            self.assertEqual(mock_doc.category_id, cat_id)
            self.assertEqual(res.title, "New Title")
            vector_store.update_payload_by_document_id.assert_awaited_once_with(
                document_id=doc_id,
                payload={"category_id": cat_id, "title": "New Title"},
            )
        asyncio.run(_test())

    def test_update_document_unassign_category(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            now = datetime.now(timezone.utc)
            doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
            cat_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef2")
            user_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef1")

            mock_doc = MagicMock(
                id=doc_id,
                title="Current Title",
                category_id=cat_id,
                file_name="test.pdf",
                file_path="uploads/test.pdf",
                file_size=1024,
                file_type="pdf",
                file_hash="hash123",
                status="indexed",
                created_by_id=user_id,
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

            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())
            res = await service.update_document(doc_id, DocumentUpdate(category_id=None))

            self.assertIsNone(mock_doc.category_id)
            category_repo.get_by_id.assert_not_called()
            vector_store.update_payload_by_document_id.assert_awaited_once_with(
                document_id=doc_id,
                payload={"category_id": None},
            )
        asyncio.run(_test())

    def test_update_document_not_found_raises(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            random_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef9")
            doc_repo.get_by_id.return_value = None
            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())

            with self.assertRaises(EntityNotFoundException):
                await service.update_document(random_id, DocumentUpdate(title="Non-existent"))
        asyncio.run(_test())

    def test_update_invalid_category_raises(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
            invalid_cat_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef9")
            mock_doc = MagicMock(id=doc_id, title="Valid Doc", category_id=None)
            doc_repo.get_by_id.return_value = mock_doc
            category_repo.get_by_id.return_value = None  # Category not found!

            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())
            with self.assertRaises(EntityNotFoundException):
                await service.update_document(doc_id, DocumentUpdate(category_id=invalid_cat_id))
        asyncio.run(_test())

    def test_soft_delete_document(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
            mock_doc = MagicMock(id=doc_id, title="Doc to Soft Delete", deleted_at=None)
            doc_repo.get_by_id.return_value = mock_doc

            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())
            await service.delete_document(doc_id)

            # Assert Qdrant vector deletion called (Hard delete vectors)
            vector_store.delete_by_document_id.assert_awaited_once_with(doc_id)
            # Assert soft_delete was called on repository (NOT hard delete)
            doc_repo.soft_delete.assert_awaited_once_with(mock_doc)
            doc_repo.delete.assert_not_called()
        asyncio.run(_test())

    def test_restore_document(self):
        async def _test():
            doc_repo = AsyncMock()
            chunk_repo = AsyncMock()
            category_repo = AsyncMock()
            embedder = AsyncMock()
            vector_store = AsyncMock()

            now = datetime.now(timezone.utc)
            doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
            chunk_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef3")
            mock_chunk = MagicMock(
                id=chunk_id,
                chunk_index=0,
                content="Nội dung điều 1 về đào tạo.",
                token_count=10,
                page_number=1,
                heading_path="Chương I > Điều 1",
            )
            mock_doc = MagicMock(
                id=doc_id,
                title="Doc to Restore",
                deleted_at=now,
                category_id=None,
                file_name="test.pdf",
                file_path="uploads/test.pdf",
                file_size=1024,
                file_type="pdf",
                file_hash="hash123",
                status="indexed",
                created_by_id=None,
                total_pages=1,
                chunk_count=1,
                error_message=None,
                created_at=now,
                updated_at=now,
                category=None,
            )
            doc_repo.get_by_id.return_value = mock_doc
            doc_repo.get_with_chunks.return_value = MagicMock(chunks=[mock_chunk])
            doc_repo.get_with_category.return_value = mock_doc
            embedder.embed_texts.return_value = MagicMock(embeddings=[[0.05] * 768])

            service = DocumentService(doc_repo, chunk_repo, category_repo, embedder, vector_store, storage_service=AsyncMock())
            restored = await service.restore_document(doc_id)

            doc_repo.restore.assert_awaited_once_with(mock_doc)
            embedder.embed_texts.assert_awaited_once_with(["Nội dung điều 1 về đào tạo."])
            vector_store.upsert_chunks.assert_awaited_once()
            self.assertEqual(restored.id, doc_id)
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
