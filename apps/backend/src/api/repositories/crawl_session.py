from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.constants.enums import CrawlItemStatus, CrawlSessionStatus
from api.core.database import async_session_factory
from api.models.crawl_session import CrawlSession, CrawlSessionItem
from api.repositories.base import BaseRepository

logger = logging.getLogger("huce_kms.crawler.repository")


class CrawlSessionRepository(BaseRepository[CrawlSession]):
    """Data access repository for crawl sessions and session items."""

    def __init__(self, session: AsyncSession):
        super().__init__(CrawlSession, session)

    async def create_session(
        self,
        session_id_str: str,
        total_urls: int,
        source_domain: str | None = None,
        started_at: datetime | None = None,
    ) -> CrawlSession:
        """Create and persist a new crawl session in PENDING or IN_PROGRESS state."""
        start_ts = started_at or datetime.now(timezone.utc)
        record = CrawlSession(
            session_id_str=session_id_str,
            status=CrawlSessionStatus.IN_PROGRESS,
            source_domain=source_domain,
            total_urls=total_urls,
            completed_urls=0,
            successful=0,
            failed=0,
            started_at=start_ts,
            duration_seconds=0.0,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def increment_progress(
        self,
        session_id_str: str,
        is_success: bool = True,
        is_fail: bool = False,
    ) -> None:
        """Atomically increment completed_urls and success/fail counts."""
        stmt = (
            update(CrawlSession)
            .where(CrawlSession.session_id_str == session_id_str)
            .values(
                completed_urls=CrawlSession.completed_urls + 1,
                successful=CrawlSession.successful + (1 if is_success else 0),
                failed=CrawlSession.failed + (1 if is_fail else 0),
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def save_item_result(
        self,
        session_id_str: str,
        item_dict: dict[str, Any],
        session_id_uuid: UUID | None = None,
    ) -> CrawlSessionItem | None:
        """Persist a single crawled page item result attached to the session."""
        target_uuid = session_id_uuid
        if not target_uuid:
            session_record = await self.get_by_session_id_str(session_id_str, load_items=False)
            if not session_record:
                logger.warning("Cannot save item: session '%s' not found.", session_id_str)
                return None
            target_uuid = session_record.id

        status_raw = item_dict.get("status", "pending")
        if isinstance(status_raw, CrawlItemStatus):
            item_status = status_raw
        elif isinstance(status_raw, int):
            item_status = CrawlItemStatus(status_raw)
        else:
            item_status = CrawlItemStatus.from_str(str(status_raw))

        page_hash = item_dict.get("page_hash")
        if not page_hash and item_dict.get("artifact_dir"):
            page_hash = Path(str(item_dict["artifact_dir"])).name
        if not page_hash and item_dict.get("url"):
            from api.services.crawler.deduplicator import Deduplicator
            page_hash = Deduplicator.hash_url(str(item_dict["url"]))

        item = CrawlSessionItem(
            session_id=target_uuid,
            url=str(item_dict.get("url", "")),
            title=item_dict.get("title"),
            page_hash=page_hash,
            status=item_status,
            duration_seconds=float(item_dict.get("duration_seconds") or 0.0),
            pdf_count=int(item_dict.get("pdf_count") or 0),
            image_count=int(item_dict.get("image_count") or 0),
            is_ingested=bool(item_dict.get("is_ingested", False)),
            ingested_at=item_dict.get("ingested_at"),
            errors=item_dict.get("errors") or [],
        )
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def complete_session(
        self,
        session_id_str: str,
        status: CrawlSessionStatus,
        duration_seconds: float,
        error_message: str | None = None,
    ) -> None:
        """Mark a crawl session completed, cancelled, or failed."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(CrawlSession)
            .where(CrawlSession.session_id_str == session_id_str)
            .values(
                status=status,
                completed_at=now,
                duration_seconds=duration_seconds,
                error_message=error_message,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_active_session(self) -> CrawlSession | None:
        """Find any currently running or pending crawl session."""
        stmt = (
            select(CrawlSession)
            .where(CrawlSession.status.in_([CrawlSessionStatus.PENDING, CrawlSessionStatus.IN_PROGRESS]))
            .order_by(desc(CrawlSession.started_at))
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_session_id_str(
        self,
        session_id_str: str,
        load_items: bool = True,
    ) -> CrawlSession | None:
        """Retrieve crawl session by human-readable string identifier."""
        stmt = select(CrawlSession).where(CrawlSession.session_id_str == session_id_str)
        if load_items:
            stmt = stmt.options(selectinload(CrawlSession.items))
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_sessions(self, limit: int = 20) -> list[CrawlSession]:
        """List past crawl sessions sorted by start time."""
        stmt = (
            select(CrawlSession)
            .options(selectinload(CrawlSession.items))
            .order_by(desc(CrawlSession.started_at))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def recover_interrupted_sessions(cls) -> int:
        """
        FastAPI lifespan startup recovery:
        Finds any session lingering in PENDING or IN_PROGRESS and transitions it to INTERRUPTED.
        """
        async with async_session_factory() as session:
            stmt = (
                update(CrawlSession)
                .where(CrawlSession.status.in_([CrawlSessionStatus.PENDING, CrawlSessionStatus.IN_PROGRESS]))
                .values(
                    status=CrawlSessionStatus.INTERRUPTED,
                    error_message="Session interrupted by system shutdown/restart.",
                    completed_at=datetime.now(timezone.utc),
                )
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount
