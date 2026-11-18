from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.document import Document
from api.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository handling database operations for Document entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_id(self, id: UUID, include_deleted: bool = False) -> Document | None:
        """Fetch document by ID, excluding soft-deleted documents unless requested."""
        doc = await super().get_by_id(id)
        if doc and not include_deleted and doc.deleted_at is not None:
            return None
        return doc

    async def get_by_file_hash(self, file_hash: str) -> Document | None:
        stmt = (
            select(Document)
            .options(selectinload(Document.category))
            .where(Document.file_hash == file_hash, Document.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_url(self, source_url: str) -> list[Document]:
        """Fetch active documents crawled from a specific source URL."""
        stmt = (
            select(Document)
            .options(selectinload(Document.category))
            .where(Document.source_url == source_url, Document.deleted_at.is_(None))
            .order_by(Document.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_category(self, document_id: UUID, include_deleted: bool = False) -> Document | None:
        stmt = (
            select(Document)
            .options(selectinload(Document.category))
            .where(Document.id == document_id)
        )
        if not include_deleted:
            stmt = stmt.where(Document.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_chunks(self, document_id: UUID, include_deleted: bool = False) -> Document | None:
        stmt = (
            select(Document)
            .options(
                selectinload(Document.category),
                selectinload(Document.chunks),
            )
            .where(Document.id == document_id)
        )
        if not include_deleted:
            stmt = stmt.where(Document.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_with_count(
        self,
        skip: int = 0,
        limit: int = 10,
        category_id: UUID | None = None,
        status: str | None = None,
        query: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[Document], int]:
        """Search documents with optional filters and pagination."""
        count_stmt = select(func.count(Document.id))
        data_stmt = (
            select(Document)
            .options(selectinload(Document.category))
            .offset(skip)
            .limit(limit)
            .order_by(Document.id.desc())
        )

        filters = []
        if not include_deleted:
            filters.append(Document.deleted_at.is_(None))
        if category_id is not None:
            filters.append(Document.category_id == category_id)
        if status is not None:
            filters.append(func.lower(Document.status) == status.strip().lower())
        if query:
            filters.append(
                or_(
                    Document.title.ilike(f"%{query}%"),
                    Document.file_name.ilike(f"%{query}%"),
                )
            )

        for f in filters:
            count_stmt = count_stmt.where(f)
            data_stmt = data_stmt.where(f)

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        data_result = await self.session.execute(data_stmt)
        documents = data_result.scalars().all()

        return documents, total
