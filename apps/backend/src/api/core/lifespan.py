import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.core.config import settings
from api.core.database import Base, engine
from api.core.seeder import seed_initial_data
import api.models

logger = logging.getLogger("huce_kms.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage FastAPI application lifecycle (startup, schema verification, storage check, shutdown)."""
    # 1. Startup phase
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        logger.error("[STARTUP] Database schema initialization failed: %s", e)
        raise

    if settings.AUTO_SEED:
        try:
            await seed_initial_data()
        except Exception as e:
            logger.error("[STARTUP] Initial data seeding error: %s", e)

    # Initialize Object Storage (MinIO bucket creation / local fallback check)
    try:
        from api.services.storage import get_storage_service
        await get_storage_service().ensure_bucket_exists()
    except Exception as e:
        logger.warning("[STARTUP] Storage service initialization check: %s", e)

    # Recover any interrupted crawler sessions left over from previous process shutdown
    try:
        from api.repositories.crawl_session import CrawlSessionRepository
        recovered_count = await CrawlSessionRepository.recover_interrupted_sessions()
        if recovered_count > 0:
            logger.info("[STARTUP] Recovered %d interrupted crawl session(s).", recovered_count)
    except Exception as e:
        logger.warning("[STARTUP] Interrupted crawl sessions recovery: %s", e)

    app.state.is_healthy = True

    # Yield control to FastAPI request handling
    yield

    # 2. Shutdown phase
    app.state.is_healthy = False
    await engine.dispose()

    # 2. Shutdown phase
    app.state.is_healthy = False
    await engine.dispose()
