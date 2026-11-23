from collections.abc import Sequence
from uuid import UUID
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.constants.enums import UserRole
from api.models.user import User
from api.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling database operations for the User model."""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_id(self, id: UUID, include_deleted: bool = False) -> User | None:
        """Fetch user by ID, excluding soft-deleted users unless requested."""
        user = await super().get_by_id(id)
        if user and not include_deleted and user.deleted_at is not None:
            return None
        return user

    async def get_by_username(self, username: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.username == username)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username_or_email(self, identifier: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(or_(User.username == identifier, User.email == identifier))
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_with_count(
        self,
        q: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 10,
        include_deleted: bool = False,
    ) -> tuple[Sequence[User], int]:
        """Search users with filtering by keyword, role, status, and pagination."""
        # 1. Build Count Query
        count_stmt = select(func.count(User.id))
        if not include_deleted:
            count_stmt = count_stmt.where(User.deleted_at.is_(None))
        if q:
            search_filter = or_(
                User.username.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
            )
            count_stmt = count_stmt.where(search_filter)
        if role is not None:
            if isinstance(role, int):
                count_stmt = count_stmt.where(User.role == role)
            elif isinstance(role, str):
                r = role.strip()
                if r and r.lower() != "all":
                    if r.isdigit():
                        count_stmt = count_stmt.where(User.role == int(r))
                    else:
                        count_stmt = count_stmt.where(User.role == UserRole.from_str(r))
        if is_active is not None:
            count_stmt = count_stmt.where(User.is_active == is_active)

        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar_one()

        # 2. Build Data Query
        data_stmt = select(User).offset(skip).limit(limit).order_by(User.id.desc())
        if not include_deleted:
            data_stmt = data_stmt.where(User.deleted_at.is_(None))
        if q:
            data_stmt = data_stmt.where(search_filter)
        if role is not None:
            if isinstance(role, int):
                data_stmt = data_stmt.where(User.role == role)
            elif isinstance(role, str):
                r = role.strip()
                if r and r.lower() != "all":
                    if r.isdigit():
                        data_stmt = data_stmt.where(User.role == int(r))
                    else:
                        data_stmt = data_stmt.where(User.role == UserRole.from_str(r))
        if is_active is not None:
            data_stmt = data_stmt.where(User.is_active == is_active)

        data_result = await self.session.execute(data_stmt)
        users = data_result.scalars().all()

        return users, total
