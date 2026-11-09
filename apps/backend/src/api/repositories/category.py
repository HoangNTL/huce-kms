from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.category import Category
from api.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository handling database operations for Category entity."""

    def __init__(self, session: AsyncSession):
        super().__init__(Category, session)

    async def get_by_slug(self, slug: str) -> Category | None:
        stmt = select(Category).where(Category.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Category | None:
        stmt = select(Category).where(Category.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[Category]:
        stmt = select(Category).order_by(Category.name.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()
