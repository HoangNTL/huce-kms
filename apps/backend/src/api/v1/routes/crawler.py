import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, status

from api.core.config import settings
from api.core.dependencies import AdminUserDep, DatabaseDep
from api.core.exceptions import BadRequestException, EntityNotFoundException
from api.repositories.category import CategoryRepository
from api.repositories.document import DocumentRepository
from api.repositories.document_chunk import DocumentChunkRepository
from api.schemas.common import BaseResponse
from api.schemas.crawler import (
    ApproveQueueRequest,
    CrawlDirectRequest,
    DiscoverRequest,
    IngestSessionRequest,
)
from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter
from api.services.crawler.registry.review_queue import ReviewQueueManager
from api.services.document import DocumentService
from api.services.rag.embedder import GeminiEmbeddingService
from api.services.rag.vector_store import QdrantVectorStore

router = APIRouter()


def get_crawler_adapter(db: DatabaseDep) -> CrawlIngestionAdapter:
    doc_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)
    cat_repo = CategoryRepository(db)
    embedder = GeminiEmbeddingService()
    vector_store = QdrantVectorStore()
    doc_service = DocumentService(
        document_repo=doc_repo,
        chunk_repo=chunk_repo,
        category_repo=cat_repo,
        embedder=embedder,
        vector_store=vector_store,
    )
    return CrawlIngestionAdapter(
        document_service=doc_service,
        document_repo=doc_repo,
        category_repo=cat_repo,
    )


@router.post(
    "/crawl",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Crawl a specific URL, extract content & media, optionally ingest to RAG (Admin only)",
)
async def crawl_direct_url(
    payload: CrawlDirectRequest,
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[dict[str, Any]]:
    engine = CrawlerCoreEngine(base_data_dir=Path(settings.CRAWLER_DATA_DIR))
    try:
        result = await engine.crawl_url(payload.url)
    except Exception as e:
        raise BadRequestException(message=f"Crawl failed for '{payload.url}': {str(e)}") from e

    response_data: dict[str, Any] = {
        "url": result.url,
        "status": result.status.value,
        "title": result.metadata.content.title if result.metadata else None,
        "content_length": len(result.markdown_content) if result.markdown_content else 0,
        "media_count": len(result.media_items),
        "page_dir": str(result.page_dir) if result.page_dir else None,
        "error_message": result.error_message,
        "ingested": False,
    }

    if payload.auto_ingest and result.page_dir:
        adapter = get_crawler_adapter(db)
        ingest_results = await adapter.ingest_page(
            page_dir=result.page_dir,
            category_id=payload.category_id,
            auto_publish=payload.auto_publish,
            uploader_id=admin.id,
        )
        response_data["ingested"] = True
        response_data["ingest_results"] = [r.model_dump() for r in ingest_results]

    return BaseResponse(
        code="CRAWL_SUCCESS",
        message=f"Successfully crawled URL: {payload.url}",
        data=response_data,
    )


@router.post(
    "/discover",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Discover candidate article URLs from category listing, sitemap or RSS (Admin only)",
)
async def discover_urls(
    payload: DiscoverRequest,
    admin: AdminUserDep,
) -> BaseResponse[dict[str, Any]]:
    discovery_engine = DiscoveryEngine()
    try:
        result = await discovery_engine.discover(payload.url, max_items=payload.max_items)
    except Exception as e:
        raise BadRequestException(message=f"Discovery failed for '{payload.url}': {str(e)}") from e

    queue_manager = ReviewQueueManager()
    saved_file = queue_manager.save_discovered(result)

    return BaseResponse(
        code="DISCOVERY_SUCCESS",
        message=f"Discovered {result.total_discovered} candidate URLs.",
        data={
            "source_url": result.source_url,
            "source_type": result.source_type.value,
            "total_discovered": result.total_discovered,
            "items": [item.model_dump() for item in result.items],
            "queue_file": saved_file.name,
        },
    )


@router.get(
    "/queue",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get discovered queue files and approved URLs (Admin only)",
)
async def get_crawl_queue(
    admin: AdminUserDep,
) -> BaseResponse[dict[str, Any]]:
    queue_dir = Path(settings.CRAWLER_DATA_DIR) / "crawl-queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    discovered_files = sorted(queue_dir.glob("discovered_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    approved_file = queue_dir / "approved.json"

    discovered_summary = []
    for df in discovered_files[:10]:
        try:
            with open(df, "r", encoding="utf-8") as f:
                data = json.load(f)
                discovered_summary.append({
                    "filename": df.name,
                    "source_url": data.get("source_url"),
                    "total": data.get("total_discovered", len(data.get("items", []))),
                    "created_at": df.stat().st_mtime,
                })
        except Exception:
            continue

    approved_urls = []
    if approved_file.exists():
        try:
            with open(approved_file, "r", encoding="utf-8") as f:
                app_data = json.load(f)
                approved_urls = app_data.get("urls", [])
        except Exception:
            pass

    return BaseResponse(
        code="QUEUE_FETCHED",
        message="Review queue fetched successfully.",
        data={
            "discovered_files": discovered_summary,
            "approved_total": len(approved_urls),
            "approved_urls": approved_urls,
        },
    )


@router.post(
    "/queue/approve",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Approve discovered URLs into the approved execution queue (Admin only)",
)
async def approve_queue_urls(
    payload: ApproveQueueRequest,
    admin: AdminUserDep,
) -> BaseResponse[dict[str, Any]]:
    queue_manager = ReviewQueueManager()
    queue_dir = queue_manager.queue_dir

    if payload.queue_file:
        safe_filename = Path(payload.queue_file).name
        target_file = queue_dir / safe_filename
    else:
        candidates = sorted(queue_dir.glob("discovered_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise EntityNotFoundException(message="No discovered candidate files found in queue.")
        target_file = candidates[0]

    if not target_file.exists():
        raise EntityNotFoundException(message=f"Queue file '{target_file.name}' not found.")

    out_file = queue_manager.approve_items(
        discovered_file=target_file,
        approved_urls=payload.approved_urls,
        approve_all=payload.approve_all,
    )

    approved = queue_manager.load_approved_urls(out_file)

    return BaseResponse(
        code="QUEUE_APPROVED",
        message=f"Approved {len(approved)} URLs for crawling.",
        data={
            "approved_file": out_file.name,
            "total_approved": len(approved),
            "urls": approved,
        },
    )


@router.post(
    "/ingest",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Ingest a crawled session or page into Document/RAG system (Admin only)",
)
async def ingest_crawl_artifacts(
    payload: IngestSessionRequest,
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[dict[str, Any]]:
    adapter = get_crawler_adapter(db)
    base_crawled = Path(settings.CRAWLER_DATA_DIR)

    if payload.page_hash:
        safe_hash = Path(payload.page_hash).name
        page_dir = base_crawled / "pages" / safe_hash
        if not page_dir.exists():
            raise EntityNotFoundException(message=f"Page directory for hash '{safe_hash}' not found.")
        results = await adapter.ingest_page(
            page_dir=page_dir,
            category_id=payload.category_id,
            auto_publish=payload.auto_publish,
            uploader_id=admin.id,
        )
        return BaseResponse(
            code="INGEST_SUCCESS",
            message=f"Ingested {len(results)} documents from page.",
            data={"results": [r.model_dump() for r in results]},
        )

    if payload.session_id:
        safe_session_id = Path(payload.session_id).name
        session_dir = base_crawled / "sessions" / safe_session_id
        if not session_dir.exists():
            raise EntityNotFoundException(message=f"Session '{safe_session_id}' not found.")
        summary = await adapter.ingest_session(
            session_dir=session_dir,
            category_id=payload.category_id,
            auto_publish=payload.auto_publish,
            uploader_id=admin.id,
        )
        return BaseResponse(
            code="INGEST_SUCCESS",
            message=f"Session ingestion completed: {summary.total_succeeded} succeeded, {summary.total_failed} failed.",
            data=summary.model_dump(),
        )

    raise BadRequestException(message="Must provide either 'session_id' or 'page_hash'.")


@router.get(
    "/sessions",
    response_model=BaseResponse[list[dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="List past crawl sessions (Admin only)",
)
async def list_crawl_sessions(
    admin: AdminUserDep,
) -> BaseResponse[list[dict[str, Any]]]:
    sessions_dir = Path(settings.CRAWLER_DATA_DIR) / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    result = []
    for s_path in sorted(sessions_dir.glob("*/session.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
        try:
            with open(s_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                result.append(data)
        except Exception:
            continue

    return BaseResponse(
        code="SESSIONS_LISTED",
        message=f"Retrieved {len(result)} crawl sessions.",
        data=result,
    )
