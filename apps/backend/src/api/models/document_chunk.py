from typing import TYPE_CHECKING, Any
from uuid import UUID
from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, TimestampMixin, uuid7

if TYPE_CHECKING:
    from api.models.document import Document


class DocumentChunk(Base, TimestampMixin):
    """Text chunk extracted from a source document, indexed in both PostgreSQL and Qdrant."""

    __tablename__ = "document_chunks"

    # UUIDv7 uniquely identifying the chunk, matching Qdrant Point ID 1-to-1
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
        index=True,
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page_start: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    page_end: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
        Index("ix_document_chunks_doc_page", "document_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id='{self.id}' doc_id={self.document_id} idx={self.chunk_index} p={self.page_start}-{self.page_end}>"
