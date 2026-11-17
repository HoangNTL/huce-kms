from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, TimestampMixin, uuid7

if TYPE_CHECKING:
    from api.models.document import Document


class Category(Base, TimestampMixin):
    """Document classification category (e.g. Quy chế, Hướng dẫn, Đồ án, Học bổng)."""

    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 1-to-many relationship: One category can group multiple documents
    documents: Mapped[list["Document"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name='{self.name}' slug='{self.slug}'>"
