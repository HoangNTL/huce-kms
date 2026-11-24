import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from api.constants.enums import CrawlSessionStatus
from api.core.config import settings
from api.core.database import async_session_factory
from api.repositories.crawl_session import CrawlSessionRepository
from api.services.crawler.registry.review_queue import ReviewQueueManager
from api.services.crawler.schemas import CrawlResult

logger = logging.getLogger("huce_kms.crawler.task_manager")


class CrawlTaskManager:
    """In-memory thread-safe registry for managing active crawl background tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}

    def register(self, session_id: str, task: asyncio.Task) -> None:
        """Register a background asyncio task associated with a crawl session."""
        self._tasks[session_id] = task

        def _cleanup(fut: asyncio.Future) -> None:
            self._tasks.pop(session_id, None)

        task.add_done_callback(_cleanup)

    def cancel(self, session_id: str) -> bool:
        """Cancel an active crawl task by session ID."""
        task = self._tasks.get(session_id)
        if task and not task.done():
            task.cancel()
            logger.info("Signalled cancellation for crawl session: %s", session_id)
            return True
        return False

    def is_active(self, session_id: str) -> bool:
        """Check if a session task is currently running."""
        task = self._tasks.get(session_id)
        return task is not None and not task.done()

    def get_active_session_id(self) -> str | None:
        """Return the session_id of any currently active task, or None."""
        for s_id, task in list(self._tasks.items()):
            if not task.done():
                return s_id
        return None

    def clear(self, session_id: str) -> None:
        """Manually clear a finished task."""
        self._tasks.pop(session_id, None)


crawl_task_manager = CrawlTaskManager()


async def run_background_crawl_session(
    session_id: str,
    urls: list[str],
    max_concurrency: int = 2,
    auto_ingest: bool = False,
    auto_publish: bool = False,
    category_id: UUID | None = None,
    clear_queue: bool = False,
    created_by_id: UUID | None = None,
    source_domain: str | None = None,
    session_uuid: UUID | None = None,
) -> None:
    """
    Background worker function that runs independent of any HTTP request lifecycle.
    Opens dedicated database sessions for every update to prevent connection leaks.
    """
    start_time = time.perf_counter()
    logger.info("Starting background crawl session '%s' with %d URLs", session_id, len(urls))

    target_uuid = session_uuid

    if not source_domain and urls:
        try:
            source_domain = urlsplit(urls[0]).netloc.lower()
        except Exception:
            source_domain = None

    # 1. Ensure persistent session in DB exists
    if not target_uuid:
        try:
            async with async_session_factory() as session:
                repo = CrawlSessionRepository(session)
                existing = await repo.get_by_session_id_str(session_id, load_items=False)
                if not existing:
                    new_sess = await repo.create_session(
                        session_id_str=session_id,
                        total_urls=len(urls),
                        source_domain=source_domain,
                    )
                    target_uuid = new_sess.id
                else:
                    target_uuid = existing.id
        except Exception as e:
            logger.error("Failed to ensure session '%s' in DB: %s", session_id, e, exc_info=True)

    # 2. Callback for real-time atomic progress update per finished URL
    async def _on_item_completed(item_res: CrawlResult, completed_count: int, total_count: int) -> None:
        is_succ = item_res.status in ("success", "partial")
        is_fail = item_res.status == "failed"
        item_dict = item_res.model_dump(mode="json")
        if not item_dict.get("page_hash") and item_res.artifact_dir:
            item_dict["page_hash"] = Path(str(item_res.artifact_dir)).name
        try:
            async with async_session_factory() as progress_session:
                p_repo = CrawlSessionRepository(progress_session)
                await p_repo.increment_progress(
                    session_id_str=session_id,
                    is_success=is_succ,
                    is_fail=is_fail,
                )
                await p_repo.save_item_result(
                    session_id_str=session_id,
                    item_dict=item_dict,
                    session_id_uuid=target_uuid,
                )
        except Exception as e:
            logger.warning("Could not persist progress for item '%s' in session '%s': %s", item_res.url, session_id, e)

    from api.services.crawler.core.engine import CrawlerCoreEngine
    engine = CrawlerCoreEngine(base_data_dir=Path(settings.CRAWLER_DATA_DIR))

    try:
        # 3. Execute batch crawl with bounded concurrency and progress callback
        batch_result = await engine.crawl_batch(
            urls=urls,
            max_concurrency=max_concurrency,
            session_id=session_id,
            on_item_completed=_on_item_completed,
        )

        duration = round(time.perf_counter() - start_time, 2)

        # 4. Mark completed in DB
        async with async_session_factory() as complete_session:
            c_repo = CrawlSessionRepository(complete_session)
            await c_repo.complete_session(
                session_id_str=session_id,
                status=CrawlSessionStatus.COMPLETED,
                duration_seconds=duration,
            )

        logger.info(
            "Crawl session '%s' completed: %d/%d succeeded in %.2fs",
            session_id,
            batch_result.successful,
            batch_result.total_urls,
            duration,
        )

        # 5. Optional auto-ingestion into Knowledge Base (PostgreSQL / Qdrant)
        if auto_ingest:
            session_dir = Path(settings.CRAWLER_DATA_DIR) / "sessions" / session_id
            if session_dir.exists():
                try:
                    from api.repositories.category import CategoryRepository
                    from api.repositories.document import DocumentRepository
                    from api.repositories.document_chunk import DocumentChunkRepository
                    from api.services.ai.managers.embedding_manager import EmbeddingManager
                    from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter
                    from api.services.document import DocumentService
                    from api.services.rag.vector_store import QdrantVectorStore

                    async with async_session_factory() as ingest_db:
                        doc_repo = DocumentRepository(ingest_db)
                        chunk_repo = DocumentChunkRepository(ingest_db)
                        cat_repo = CategoryRepository(ingest_db)
                        vector_store = QdrantVectorStore()
                        embedder = EmbeddingManager()
                        doc_service = DocumentService(
                            document_repo=doc_repo,
                            chunk_repo=chunk_repo,
                            category_repo=cat_repo,
                            embedder=embedder,
                            vector_store=vector_store,
                        )
                        adapter = CrawlIngestionAdapter(
                            document_service=doc_service,
                            document_repo=doc_repo,
                            category_repo=cat_repo,
                        )
                        await adapter.ingest_session(
                            session_dir=session_dir,
                            category_id=category_id,
                            auto_publish=auto_publish,
                            created_by_id=created_by_id,
                        )
                        logger.info("Auto-ingestion completed for session '%s'", session_id)
                except Exception as ingest_err:
                    logger.error("Auto-ingest error for session '%s': %s", session_id, ingest_err, exc_info=True)

        # 6. Clear approved queue if requested
        if clear_queue:
            try:
                q_manager = ReviewQueueManager()
                q_manager.clear_approved_queue()
            except Exception as q_err:
                logger.warning("Could not clear approved queue after session '%s': %s", session_id, q_err)

    except asyncio.CancelledError:
        duration = round(time.perf_counter() - start_time, 2)
        logger.warning("Crawl session '%s' was cancelled after %.2fs", session_id, duration)
        try:
            async with async_session_factory() as cancel_session:
                cancel_repo = CrawlSessionRepository(cancel_session)
                await cancel_repo.complete_session(
                    session_id_str=session_id,
                    status=CrawlSessionStatus.CANCELLED,
                    duration_seconds=duration,
                    error_message="Phiên thu thập bị hủy bởi người dùng.",
                )
        except Exception as e:
            logger.error("Could not write CANCELLED status for session '%s': %s", session_id, e)
        raise

    except Exception as exc:
        duration = round(time.perf_counter() - start_time, 2)
        logger.error("Crawl session '%s' failed unexpectedly: %s", session_id, exc, exc_info=True)
        try:
            async with async_session_factory() as err_session:
                err_repo = CrawlSessionRepository(err_session)
                await err_repo.complete_session(
                    session_id_str=session_id,
                    status=CrawlSessionStatus.FAILED,
                    duration_seconds=duration,
                    error_message=str(exc),
                )
        except Exception as e:
            logger.error("Could not write FAILED status for session '%s': %s", session_id, e)

    finally:
        crawl_task_manager.clear(session_id)
