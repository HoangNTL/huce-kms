import os
import time
from datetime import datetime
from uuid import UUID
from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from api.core.config import settings

# 1. Initialize Async Engine (SQL logging controlled cleanly via logging.py + SQL_ECHO)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# 2. Initialize Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


def uuid7() -> UUID:
    """Generate an RFC 9562 compliant UUIDv7 (timestamp-ordered 128-bit UUID)."""
    ms = int(time.time() * 1000)
    rand_bytes = os.urandom(10)
    time_high = (ms >> 16) & 0xFFFFFFFF
    time_low = ms & 0xFFFF
    time_hi_and_version = (0x7 << 12) | (int.from_bytes(rand_bytes[:2], "big") & 0x0FFF)
    clock_seq = (0x80 | (rand_bytes[2] & 0x3F)) << 8 | rand_bytes[3]
    node = int.from_bytes(rand_bytes[4:10], "big")
    return UUID(fields=(time_high, time_low, time_hi_and_version, clock_seq >> 8, clock_seq & 0xFF, node))


# 3. SQLAlchemy 2.0 Base Model
class Base(AsyncAttrs, DeclarativeBase):
    """Base declarative class for all ORM models."""

    pass


class TimestampMixin:
    """Mixin providing automatic created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin providing soft-delete support via deleted_at timestamp."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Check whether the record has been soft-deleted."""
        return self.deleted_at is not None
