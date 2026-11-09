from typing import TYPE_CHECKING
from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.category import Category
    from api.models.document_chunk import DocumentChunk
    from api.models.user import User


class Document(Base, TimestampMixin):
    """Document entity tracking uploaded source files (PDF, DOCX) and their ingestion status."""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # Ingestion Status: "UPLOADED" | "PROCESSING" | "INDEXED" | "FAILED"
    status: Mapped[str] = mapped_column(String(20), default="UPLOADED", nullable=False, index=True)

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    uploader_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    category: Mapped["Category | None"] = relationship(back_populates="documents")
    uploader: Mapped["User | None"] = relationship()
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title='{self.title}' status='{self.status}' chunks={self.chunk_count}>"
