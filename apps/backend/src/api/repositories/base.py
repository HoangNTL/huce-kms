from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic base repository providing fundamental CRUD database operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, id: Any) -> ModelType | None:
        """Fetch a single record by primary key."""
        return await self.session.get(self.model, id)

    async def list(self, skip: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """Fetch a paginated list of records."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, instance: ModelType) -> ModelType:
        """Persist a new record to database."""
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelType) -> ModelType:
        """Flush changes to update existing record."""
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete an existing record."""
        await self.session.delete(instance)
        await self.session.flush()

    async def soft_delete(self, instance: ModelType) -> ModelType:
        """Mark record as soft-deleted by setting deleted_at to current UTC timestamp."""
        if hasattr(instance, "deleted_at"):
            from datetime import datetime, timezone

            instance.deleted_at = datetime.now(timezone.utc)
            await self.session.flush()
            await self.session.refresh(instance)
        else:
            await self.delete(instance)
        return instance

    async def restore(self, instance: ModelType) -> ModelType:
        """Restore a soft-deleted record by clearing deleted_at."""
        if hasattr(instance, "deleted_at"):
            instance.deleted_at = None
            await self.session.flush()
            await self.session.refresh(instance)
        return instance
