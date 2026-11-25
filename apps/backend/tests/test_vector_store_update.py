import unittest
from unittest.mock import AsyncMock, MagicMock
from api.services.rag.vector_store import QdrantVectorStore


class TestVectorStoreUpdate(unittest.IsolatedAsyncioTestCase):
    async def test_update_payload_by_document_id(self):
        store = QdrantVectorStore()
        mock_client = AsyncMock()
        store._client = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[MagicMock(name=store.collection_name)])

        await store.update_payload_by_document_id(
            document_id=123,
            payload={"title": "Updated Title", "category_id": 5},
        )
        mock_client.set_payload.assert_awaited_once()

    async def test_search_with_metadata_filters(self):
        store = QdrantVectorStore()
        mock_client = AsyncMock()
        store._client = mock_client
        mock_client.get_collections.return_value = MagicMock(collections=[MagicMock(name=store.collection_name)])
        mock_client.query_points.return_value = MagicMock(
            points=[MagicMock(id="chunk-1", score=0.92, payload={"content": "Điều 1", "metadata": {"doc_type": "decision"}})]
        )

        results = await store.search(
            query_vector=[0.1, 0.2],
            limit=3,
            category_id=42,
            metadata_filters={"doc_type": "decision", "year": 2024, "ignored": None},
        )

        mock_client.query_points.assert_awaited_once()
        kwargs = mock_client.query_points.call_args.kwargs
        self.assertEqual(kwargs["limit"], 3)
        must_conditions = kwargs["query_filter"].must
        condition_map = {c.key: c.match.value for c in must_conditions}
        self.assertEqual(
            condition_map,
            {
                "category_id": "42",
                "metadata.doc_type": "decision",
                "metadata.year": 2024,
            },
        )
        self.assertEqual(
            results,
            [{"id": "chunk-1", "score": 0.92, "payload": {"content": "Điều 1", "metadata": {"doc_type": "decision"}}}],
        )


if __name__ == "__main__":
    unittest.main()
