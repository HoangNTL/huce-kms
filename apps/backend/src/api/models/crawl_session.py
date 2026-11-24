from datetime import datetime
from typing import Any
from uuid import UUID
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.constants.enums import CrawlItemStatus, CrawlSessionStatus
from api.core.database import Base, TimestampMixin, uuid7


class CrawlSession(Base, TimestampMixin):
    """
    Tracks execution metadata and progress for batch web crawling sessions.
    """
    __tablename__ = "crawl_sessions"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
    )
    # Human-readable / deterministic timestamp ID (e.g. "2026-11-23_180000")
    session_id_str: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # 0=PENDING, 1=IN_PROGRESS, 2=COMPLETED, 3=FAILED, 4=CANCELLED, 5=INTERRUPTED
    status: Mapped[int] = mapped_column(SmallInteger, default=CrawlSessionStatus.PENDING, nullable=False, index=True)
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    total_urls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_urls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 1-to-many relationship with session items
    items: Mapped[list["CrawlSessionItem"]] = relationship(
        "CrawlSessionItem",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_crawl_sessions_status_started_at", "status", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<CrawlSession {self.session_id_str} status={self.status} {self.completed_urls}/{self.total_urls}>"


class CrawlSessionItem(Base, TimestampMixin):
    """
    Individual URL outcome within a batch crawl session.
    """
    __tablename__ = "crawl_session_items"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid7,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("crawl_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page_hash: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # 0=PENDING, 1=RUNNING, 2=SUCCESS, 3=PARTIAL, 4=FAILED, 5=SKIPPED
    status: Mapped[int] = mapped_column(SmallInteger, default=CrawlItemStatus.PENDING, nullable=False, index=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    pdf_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_ingested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    errors: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)

    session: Mapped["CrawlSession"] = relationship("CrawlSession", back_populates="items")

    __table_args__ = (
        Index("ix_crawl_session_items_session_status", "session_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<CrawlSessionItem {self.url} status={self.status}>"
