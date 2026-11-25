from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.constants.enums import DocumentStatus
from api.core.database import async_session_factory
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

    async def is_active(self, document_id: UUID) -> bool:
        """Query PostgreSQL directly to confirm document exists and is not soft-deleted."""
        stmt = select(Document.id).where(Document.id == document_id, Document.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

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
            if isinstance(status, int):
                filters.append(Document.status == status)
            elif isinstance(status, str):
                s = status.strip()
                if s and s.lower() != "all":
                    if s.isdigit():
                        filters.append(Document.status == int(s))
                    else:
                        filters.append(Document.status == DocumentStatus.from_str(s))
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

    @classmethod
    async def recover_interrupted_documents(cls) -> int:
        """Mark any documents stuck in PROCESSING after a server restart as FAILED."""
        async with async_session_factory() as session:
            stmt = (
                update(Document)
                .where(Document.status == DocumentStatus.PROCESSING)
                .values(
                    status=DocumentStatus.FAILED,
                    error_message="Quá trình xử lý tài liệu bị gián đoạn do máy chủ khởi động lại. Vui lòng thử xử lý lại.",
                )
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount or 0
