from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, TimestampMixin, uuid7

if TYPE_CHECKING:
    from api.models.user import User


class RefreshToken(Base, TimestampMixin):
    """Stores user session refresh tokens for multi-device management & token rotation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    # Client metadata for auditing & session inspection
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    # Relationship back to User
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.is_revoked}>"
