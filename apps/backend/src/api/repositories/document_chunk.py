from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.document_chunk import DocumentChunk
from api.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository handling database operations for DocumentChunk entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)

    async def create_bulk(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        """Persist multiple document chunks in a single flush operation."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get_by_document_id(self, document_id: UUID) -> Sequence[DocumentChunk]:
        """Fetch all chunks for a given document ordered by chunk_index."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete_by_document_id(self, document_id: UUID) -> int:
        """Delete all chunks belonging to a document."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0
