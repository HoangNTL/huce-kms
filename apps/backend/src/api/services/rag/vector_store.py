import logging
from typing import Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from api.core.config import settings

logger = logging.getLogger("huce_kms.rag.vector_store")


class QdrantVectorStore:
    """Manages document chunk vector indexing and retrieval via Qdrant."""

    def __init__(
        self,
        collection_name: str = settings.QDRANT_COLLECTION_NAME,
        vector_dimension: int = settings.VECTOR_DIMENSION,
    ):
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self._client: AsyncQdrantClient | None = None

    def get_client(self) -> AsyncQdrantClient:
        """Get or initialize AsyncQdrantClient instance."""
        if self._client is None:
            api_key = settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None
            self._client = AsyncQdrantClient(
                url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
                api_key=api_key,
                https=False,
                check_compatibility=False,
            )
        return self._client

    async def ensure_collection(self) -> None:
        """Verify that the target collection exists, or create it with Cosine distance."""
        client = self.get_client()
        collections_response = await client.get_collections()
        existing = [c.name for c in collections_response.collections]

        if self.collection_name not in existing:
            await client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: '%s' (dim=%d)", self.collection_name, self.vector_dimension)

    async def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        """Upsert a batch of chunk vectors and metadata payloads into Qdrant."""
        if not chunks or not embeddings:
            return

        await self.ensure_collection()
        client = self.get_client()

        points = [
            PointStruct(
                id=chunk["id"],
                vector=vector,
                payload={
                    "document_id": chunk["document_id"],
                    "title": chunk.get("title", ""),
                    "category_id": chunk.get("category_id"),
                    "chunk_index": chunk["chunk_index"],
                    "page_number": chunk["page_number"],
                    "content": chunk["content"],
                },
            )
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ]

        await client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("Upserted %d points to Qdrant collection '%s'", len(points), self.collection_name)

    async def delete_by_document_id(self, document_id: int) -> None:
        """Delete all points associated with a specific document."""
        await self.ensure_collection()
        client = self.get_client()

        await client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )
        logger.info("Deleted Qdrant points for document_id=%d", document_id)

    async def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        category_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search similar document chunks by vector similarity."""
        await self.ensure_collection()
        client = self.get_client()

        query_filter = None
        if category_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="category_id",
                        match=MatchValue(value=category_id),
                    )
                ]
            )

        results = await client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        scored_points = []
        for pt in results.points:
            scored_points.append({
                "id": str(pt.id),
                "score": pt.score,
                "payload": pt.payload or {},
            })

        return scored_points

    async def close(self) -> None:
        """Close Qdrant client connection if open."""
        if self._client is not None:
            await self._client.close()
            self._client = None
