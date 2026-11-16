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


if __name__ == "__main__":
    unittest.main()
