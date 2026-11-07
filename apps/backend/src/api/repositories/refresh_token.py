from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.refresh_token import RefreshToken
from api.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository handling database operations for refresh tokens / user sessions."""

    def __init__(self, session: AsyncSession):
        super().__init__(RefreshToken, session)

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Fetch active or revoked refresh token by string."""
        stmt = select(RefreshToken).where(RefreshToken.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_record: RefreshToken) -> None:
        """Mark a single refresh token as revoked."""
        token_record.is_revoked = True
        await self.session.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user (logout all devices / security incident)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
            .values(is_revoked=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()
