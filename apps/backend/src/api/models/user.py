from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import Boolean, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, SoftDeleteMixin, TimestampMixin, uuid7

if TYPE_CHECKING:
    from api.models.refresh_token import RefreshToken


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account entity. System supports strictly two roles: 'user' and 'admin'."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
        index=True,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # "user" or "admin"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 1-to-many relationship: One user can have multiple active refresh tokens / devices
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
