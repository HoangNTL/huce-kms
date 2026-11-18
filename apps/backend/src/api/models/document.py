from typing import TYPE_CHECKING
from uuid import UUID
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, SoftDeleteMixin, TimestampMixin, uuid7

if TYPE_CHECKING:
    from api.models.category import Category
    from api.models.document_chunk import DocumentChunk
    from api.models.user import User


class Document(Base, TimestampMixin, SoftDeleteMixin):
    """Document entity tracking uploaded source files (PDF, DOCX) and their ingestion status."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Source tracking: URL (if crawled) and source type ("upload" | "crawler")
    source_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="upload", nullable=False, index=True)

    # Ingestion Status: "uploaded" | "pending" | "processing" | "indexed" | "failed"
    status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False, index=True)

    category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    category: Mapped["Category | None"] = relationship(back_populates="documents")
    created_by: Mapped["User | None"] = relationship()
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title='{self.title}' status='{self.status}' chunks={self.chunk_count}>"
