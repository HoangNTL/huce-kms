import asyncio
from datetime import datetime, timezone
import json
import mimetypes
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse

from api.constants.enums import CrawlItemStatus, CrawlSessionStatus
from api.core.config import settings
from api.core.dependencies import AdminUserDep, DatabaseDep
from api.core.exceptions import BadRequestException, ConflictException, EntityNotFoundException
from api.repositories.category import CategoryRepository
from api.repositories.crawl_session import CrawlSessionRepository
from api.repositories.document import DocumentRepository
from api.repositories.document_chunk import DocumentChunkRepository
from api.schemas.common import BaseResponse
from api.schemas.crawler import (
    ApproveQueueRequest,
    CrawlDirectRequest,
    DiscoverRequest,
    IngestSessionRequest,
    RemoveQueueItemRequest,
    StartQueueRequest,
    StartQueueResponse,
)
from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter
from api.services.crawler.registry.review_queue import ReviewQueueManager
from api.services.crawler.task_manager import crawl_task_manager, run_background_crawl_session
from api.services.document import DocumentService
from api.services.rag.vector_store import QdrantVectorStore
from api.v1.routes.rag import get_embedding_manager

router = APIRouter()


def get_crawler_adapter(
    db: DatabaseDep,
    embedder: Annotated[EmbeddingManager, Depends(get_embedding_manager)],
) -> CrawlIngestionAdapter:
    doc_repo = DocumentRepository(db)
    chunk_repo = DocumentChunkRepository(db)
    cat_repo = CategoryRepository(db)
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


CrawlerAdapterDep = Annotated[CrawlIngestionAdapter, Depends(get_crawler_adapter)]


def _enrich_item_with_artifacts(page_hash: str | None, base_data_dir: Path) -> dict[str, Any]:
    """Inspect the page artifact directory for PDFs, images, content, and ingestion state."""
    pdf_list: list[dict[str, Any]] = []
    img_list: list[dict[str, Any]] = []
    markdown_content = ""
    is_meaningful = True
    has_ocr = False
    is_ingested = False
    ingested_at = None

    if page_hash:
        safe_hash = Path(page_hash).name
        art_dir = base_data_dir / "pages" / safe_hash
        if art_dir.exists() and art_dir.is_dir():
            ingest_file = art_dir / "ingestion.json"
            if ingest_file.exists():
                is_ingested = True
                try:
                    with open(ingest_file, "r", encoding="utf-8") as f:
                        ing_data = json.load(f)
                        ingested_at = ing_data.get("ingested_at")
                except Exception:
                    pass

            pdfs_dir = art_dir / "pdfs"
            if pdfs_dir.exists() and pdfs_dir.is_dir():
                for p in sorted(pdfs_dir.glob("*")):
                    if p.is_file():
                        pdf_list.append({
                            "name": p.name,
                            "size": p.stat().st_size,
                            "url": f"/api/v1/crawler/media/{safe_hash}/pdfs/{p.name}",
                        })

            imgs_dir = art_dir / "images"
            if imgs_dir.exists() and imgs_dir.is_dir():
                for img in sorted(imgs_dir.glob("*")):
                    if img.is_file():
                        img_list.append({
                            "name": img.name,
                            "size": img.stat().st_size,
                            "url": f"/api/v1/crawler/media/{safe_hash}/images/{img.name}",
                        })

            content_file = art_dir / "content.md"
            if content_file.exists():
                try:
                    markdown_content = content_file.read_text(encoding="utf-8")
                except Exception:
                    markdown_content = ""

            is_meaningful = CrawlIngestionAdapter.is_meaningful_markdown(markdown_content)
            has_ocr = "## Nội dung trích xuất từ văn bản đính kèm" in markdown_content

    return {
        "pdf_count": len(pdf_list),
        "image_count": len(img_list),
        "pdfs": pdf_list,
        "images": img_list,
        "markdown_content": markdown_content,
        "markdown_length": len(markdown_content),
        "is_meaningful_markdown": is_meaningful,
        "has_ocr": has_ocr,
        "is_ingested": is_ingested,
        "ingested_at": ingested_at,
    }


@router.post(
    "/crawl",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Crawl a specific URL, extract content & media, optionally ingest to RAG (Admin only)",
)
async def crawl_direct_url(
    payload: CrawlDirectRequest,
    admin: AdminUserDep,
    adapter: CrawlerAdapterDep,
) -> BaseResponse[dict[str, Any]]:
    engine = CrawlerCoreEngine(base_data_dir=Path(settings.CRAWLER_DATA_DIR))
    try:
        result = await engine.crawl_url(payload.url)
    except Exception as e:
        raise BadRequestException(message=f"Crawl failed for '{payload.url}': {str(e)}") from e

    content_len = 0
    if result.markdown_path and result.markdown_path.exists():
        try:
            content_len = result.markdown_path.stat().st_size
        except Exception:
            content_len = 0

    status_val = getattr(result.status, "value", str(result.status))
    error_msg = "; ".join(result.errors) if result.errors else None

    response_data: dict[str, Any] = {
        "url": result.url,
        "status": status_val,
        "title": result.title,
        "content_length": content_len,
        "media_count": result.pdf_count + result.image_count,
        "page_dir": str(result.artifact_dir) if result.artifact_dir else None,
        "error_message": error_msg,
        "ingested": False,
        "published": False,
    }

    if payload.auto_ingest and result.artifact_dir:
        ingest_results = await adapter.ingest_page(
            page_dir=result.artifact_dir,
            category_id=payload.category_id,
            auto_publish=payload.auto_publish,
            created_by_id=admin.id,
        )
        response_data["ingested"] = True
        response_data["published"] = bool(payload.auto_publish)
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
            "source_type": getattr(result.source_type, "value", str(result.source_type)),
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
    "/queue/start",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start crawling all approved URLs asynchronously in background (Admin only)",
)
async def start_crawling_queue(
    payload: StartQueueRequest,
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[dict[str, Any]]:
    session_repo = CrawlSessionRepository(db)

    # 1. Check for active session concurrency
    active_in_mem = crawl_task_manager.get_active_session_id()
    active_in_db = await session_repo.get_active_session()
    if active_in_mem or active_in_db:
        running_id = active_in_mem or (active_in_db.session_id_str if active_in_db else "unknown")
        raise ConflictException(
            message=f"Phiên thu thập '{running_id}' đang diễn ra. Vui lòng đợi phiên hiện tại kết thúc hoặc bấm hủy."
        )

    # 2. Check approved queue
    queue_manager = ReviewQueueManager()
    approved_file = queue_manager.queue_dir / "approved.json"
    if not approved_file.exists():
        raise BadRequestException(message="Hàng đợi duyệt hiện đang trống.")

    urls = queue_manager.load_approved_urls(approved_file)
    if not urls:
        raise BadRequestException(message="Hàng đợi duyệt hiện không có liên kết nào để thu thập.")

    # 3. Create session record in DB
    now_utc = datetime.now(timezone.utc)
    session_id = f"batch_{now_utc.strftime('%Y%m%d_%H%M%S')}"
    source_domain = None
    try:
        source_domain = urlparse(urls[0]).netloc
    except Exception:
        pass

    db_session = await session_repo.create_session(
        session_id_str=session_id,
        total_urls=len(urls),
        source_domain=source_domain,
        started_at=now_utc,
    )

    # 4. Spawn background worker
    bg_task = asyncio.create_task(
        run_background_crawl_session(
            session_id=session_id,
            urls=urls,
            max_concurrency=payload.max_concurrency,
            auto_ingest=payload.auto_ingest,
            auto_publish=payload.auto_publish,
            category_id=payload.category_id,
            clear_queue=payload.clear_queue,
            created_by_id=admin.id,
            source_domain=source_domain,
            session_uuid=db_session.id,
        )
    )
    crawl_task_manager.register(session_id, bg_task)

    response_dto = StartQueueResponse(
        session_id=session_id,
        status="in_progress",
        total_urls=len(urls),
        message="Phiên thu thập đã được khởi chạy ngầm thành công. Bạn có thể theo dõi tiến độ theo thời gian thực.",
    )

    return BaseResponse(
        code="QUEUE_CRAWL_STARTED",
        message=f"Đã bắt đầu phiên thu thập ngầm cho {len(urls)} liên kết.",
        data=response_dto.model_dump(),
    )


@router.delete(
    "/queue",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Clear all URLs from approved queue (Admin only)",
)
async def clear_crawl_queue(admin: AdminUserDep) -> BaseResponse[dict[str, Any]]:
    queue_manager = ReviewQueueManager()
    queue_manager.clear_approved_queue()
    return BaseResponse(
        code="QUEUE_CLEARED",
        message="Đã xóa toàn bộ liên kết trong hàng đợi duyệt.",
        data={"approved_total": 0, "approved_urls": []},
    )


@router.delete(
    "/queue/item",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Remove a specific URL from approved queue (Admin only)",
)
async def remove_queue_item(
    url: str,
    admin: AdminUserDep,
) -> BaseResponse[dict[str, Any]]:
    queue_manager = ReviewQueueManager()
    updated = queue_manager.remove_approved_url(url)
    return BaseResponse(
        code="QUEUE_ITEM_REMOVED",
        message="Đã xóa liên kết khỏi hàng đợi duyệt.",
        data={"approved_total": len(updated), "approved_urls": updated},
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
    adapter: CrawlerAdapterDep,
) -> BaseResponse[dict[str, Any]]:
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
            created_by_id=admin.id,
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
            created_by_id=admin.id,
        )
        return BaseResponse(
            code="INGEST_SUCCESS",
            message=f"Session ingestion completed: {summary.successful} succeeded, {summary.failed} failed.",
            data=summary.model_dump(),
        )

    raise BadRequestException(message="Must provide either 'session_id' or 'page_hash'.")


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Cancel an active crawl session (Admin only)",
)
async def cancel_crawl_session(
    session_id: str,
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[dict[str, Any]]:
    safe_session_id = Path(session_id).name
    is_cancelled = crawl_task_manager.cancel(safe_session_id)

    if not is_cancelled:
        session_repo = CrawlSessionRepository(db)
        db_session = await session_repo.get_by_session_id_str(safe_session_id, load_items=False)
        if db_session and db_session.status in (CrawlSessionStatus.PENDING, CrawlSessionStatus.IN_PROGRESS):
            await session_repo.complete_session(
                session_id_str=safe_session_id,
                status=CrawlSessionStatus.CANCELLED,
                duration_seconds=db_session.duration_seconds or 0.0,
                error_message="Phiên đã bị hủy bởi quản trị viên.",
            )
            return BaseResponse(
                code="SESSION_CANCELLED",
                message=f"Đã cập nhật trạng thái hủy cho phiên '{safe_session_id}'.",
                data={"session_id": safe_session_id, "status": "cancelled"},
            )
        return BaseResponse(
            code="SESSION_NOT_ACTIVE",
            message=f"Phiên '{safe_session_id}' không đang chạy hoặc đã kết thúc.",
            data={
                "session_id": safe_session_id,
                "status": (
                    CrawlSessionStatus(db_session.status).name_str
                    if db_session and isinstance(db_session.status, int)
                    else (db_session.status.name_str if hasattr(db_session.status, "name_str") else "unknown")
                ) if db_session else "unknown",
            },
        )

    return BaseResponse(
        code="SESSION_CANCELLED",
        message=f"Đã gửi tín hiệu hủy phiên thu thập '{safe_session_id}'.",
        data={"session_id": safe_session_id, "status": "cancelled"},
    )


@router.get(
    "/sessions",
    response_model=BaseResponse[list[dict[str, Any]]],
    status_code=status.HTTP_200_OK,
    summary="List past crawl sessions (Admin only)",
)
async def list_crawl_sessions(
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[list[dict[str, Any]]]:
    session_repo = CrawlSessionRepository(db)
    db_sessions = await session_repo.list_sessions(limit=50)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for s in db_sessions:
        seen_ids.add(s.session_id_str)
        if isinstance(s.status, int):
            status_name = CrawlSessionStatus(s.status).name_str
        elif hasattr(s.status, "name_str"):
            status_name = s.status.name_str
        elif hasattr(s.status, "name"):
            status_name = s.status.name.lower()
        else:
            status_name = str(s.status).lower()
        results.append({
            "session_id": s.session_id_str,
            "status": status_name,
            "total_urls": s.total_urls,
            "completed_urls": s.completed_urls,
            "successful": s.successful,
            "failed": s.failed,
            "duration_seconds": s.duration_seconds,
            "source_domain": s.source_domain,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "error_message": s.error_message,
        })

    # Legacy filesystem fallback for sessions not yet in DB
    sessions_dir = Path(settings.CRAWLER_DATA_DIR) / "sessions"
    if sessions_dir.exists():
        for s_path in sorted(sessions_dir.glob("*/session.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]:
            sid = s_path.parent.name
            if sid in seen_ids:
                continue
            try:
                with open(s_path, "r", encoding="utf-8") as f:
                    legacy_data = json.load(f)
                    if not legacy_data.get("session_id"):
                        legacy_data["session_id"] = sid
                    results.append(legacy_data)
                    seen_ids.add(sid)
            except Exception:
                continue

    return BaseResponse(
        code="SESSIONS_LISTED",
        message=f"Retrieved {len(results)} crawl sessions.",
        data=results,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get detailed crawl session results and artifacts for inspection (Admin only)",
)
async def get_crawl_session_details(
    session_id: str,
    admin: AdminUserDep,
    db: DatabaseDep,
) -> BaseResponse[dict[str, Any]]:
    safe_session_id = Path(session_id).name
    base_data_dir = Path(settings.CRAWLER_DATA_DIR)
    session_repo = CrawlSessionRepository(db)

    # 1. Try DB first
    db_session = await session_repo.get_by_session_id_str(safe_session_id, load_items=True)
    if db_session:
        if isinstance(db_session.status, int):
            session_status_str = CrawlSessionStatus(db_session.status).name_str
        elif hasattr(db_session.status, "name_str"):
            session_status_str = db_session.status.name_str
        elif hasattr(db_session.status, "name"):
            session_status_str = db_session.status.name.lower()
        else:
            session_status_str = str(db_session.status).lower()

        session_data = {
            "session_id": db_session.session_id_str,
            "status": session_status_str,
            "total_urls": db_session.total_urls,
            "completed_urls": db_session.completed_urls,
            "successful": db_session.successful,
            "failed": db_session.failed,
            "duration_seconds": db_session.duration_seconds,
            "source_domain": db_session.source_domain,
            "started_at": db_session.started_at.isoformat() if db_session.started_at else None,
            "completed_at": db_session.completed_at.isoformat() if db_session.completed_at else None,
            "error_message": db_session.error_message,
        }

        detailed_items = []
        for item in db_session.items:
            item_hash = item.page_hash
            if not item_hash:
                from api.services.crawler.deduplicator import Deduplicator
                item_hash = Deduplicator.hash_url(item.url)

            if isinstance(item.status, int):
                item_status_str = CrawlItemStatus(item.status).name_str
            elif hasattr(item.status, "name_str"):
                item_status_str = item.status.name_str
            elif hasattr(item.status, "name"):
                item_status_str = item.status.name.lower()
            else:
                item_status_str = str(item.status).lower()

            enriched = _enrich_item_with_artifacts(item_hash, base_data_dir)
            detailed_items.append({
                "url": item.url,
                "title": item.title or "",
                "status": item_status_str,
                "page_hash": item_hash or "",
                "duration_seconds": item.duration_seconds,
                "pdf_count": enriched["pdf_count"],
                "image_count": enriched["image_count"],
                "pdfs": enriched["pdfs"],
                "images": enriched["images"],
                "markdown_content": enriched["markdown_content"],
                "markdown_length": enriched["markdown_length"],
                "is_meaningful_markdown": enriched["is_meaningful_markdown"],
                "has_ocr": enriched["has_ocr"],
                "is_ingested": item.is_ingested or enriched["is_ingested"],
                "ingested_at": item.ingested_at.isoformat() if item.ingested_at else (enriched["ingested_at"] if isinstance(enriched["ingested_at"], str) else None),
                "errors": item.errors or [],
            })

        return BaseResponse(
            code="SESSION_DETAILS_FETCHED",
            message=f"Chi tiết phiên thu thập {safe_session_id}",
            data={
                "session": session_data,
                "items": detailed_items,
            },
        )

    # 2. Fallback to legacy filesystem session.json and results.json
    session_dir = base_data_dir / "sessions" / safe_session_id
    if not session_dir.exists():
        raise EntityNotFoundException(message=f"Phiên thu thập '{safe_session_id}' không tồn tại.")

    session_info_path = session_dir / "session.json"
    results_path = session_dir / "results.json"

    session_data = {"session_id": safe_session_id}
    if session_info_path.exists():
        try:
            with open(session_info_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except Exception:
            pass

    raw_items = []
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
        except Exception:
            pass

    detailed_items = []
    for it in raw_items:
        art_dir_str = it.get("artifact_dir")
        page_hash = Path(art_dir_str).name if art_dir_str else (it.get("page_hash") or "")
        enriched = _enrich_item_with_artifacts(page_hash, base_data_dir)

        detailed_items.append({
            "url": it.get("url", ""),
            "title": it.get("title", ""),
            "status": it.get("status", "unknown"),
            "page_hash": page_hash,
            "duration_seconds": it.get("duration_seconds", 0),
            "pdf_count": enriched["pdf_count"],
            "image_count": enriched["image_count"],
            "pdfs": enriched["pdfs"],
            "images": enriched["images"],
            "markdown_content": enriched["markdown_content"],
            "markdown_length": enriched["markdown_length"],
            "is_meaningful_markdown": enriched["is_meaningful_markdown"],
            "has_ocr": enriched["has_ocr"],
            "is_ingested": enriched["is_ingested"],
            "ingested_at": enriched["ingested_at"],
            "errors": it.get("errors", []),
        })

    return BaseResponse(
        code="SESSION_DETAILS_FETCHED",
        message=f"Chi tiết phiên thu thập {safe_session_id}",
        data={
            "session": session_data,
            "items": detailed_items,
        },
    )


@router.get(
    "/media/{page_hash}/{media_type}/{filename}",
    summary="Download or preview an artifact file (PDF, image) from a crawled page",
)
async def get_crawl_media_file(
    page_hash: str,
    media_type: str,
    filename: str,
):
    safe_hash = Path(page_hash).name
    safe_media = Path(media_type).name
    safe_name = Path(filename).name

    if safe_media not in ("pdfs", "images"):
        raise BadRequestException(message="Danh mục media không hợp lệ.")

    base_pages_dir = (Path(settings.CRAWLER_DATA_DIR) / "pages").resolve()
    file_path = (base_pages_dir / safe_hash / safe_media / safe_name).resolve()

    if not file_path.is_relative_to(base_pages_dir) or not file_path.exists() or not file_path.is_file():
        raise EntityNotFoundException(message="Tệp media không tồn tại hoặc đã bị xóa.")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/pdf" if safe_media == "pdfs" else "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=safe_name,
        content_disposition_type="inline",
    )
