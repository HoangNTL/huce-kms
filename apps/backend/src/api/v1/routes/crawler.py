import json
import mimetypes
from pathlib import Path
from typing import Annotated, Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse

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
    RemoveQueueItemRequest,
    StartQueueRequest,
)
from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter
from api.services.crawler.registry.review_queue import ReviewQueueManager
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
    }

    if payload.auto_ingest and result.artifact_dir:
        ingest_results = await adapter.ingest_page(
            page_dir=result.artifact_dir,
            category_id=payload.category_id,
            auto_publish=payload.auto_publish,
            created_by_id=admin.id,
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
    status_code=status.HTTP_200_OK,
    summary="Start crawling all approved URLs in the queue (Admin only)",
)
async def start_crawling_queue(
    payload: StartQueueRequest,
    admin: AdminUserDep,
    adapter: CrawlerAdapterDep,
) -> BaseResponse[dict[str, Any]]:
    queue_manager = ReviewQueueManager()
    approved_file = queue_manager.queue_dir / "approved.json"
    if not approved_file.exists():
        raise BadRequestException(message="Hàng đợi duyệt hiện đang trống.")

    urls = queue_manager.load_approved_urls(approved_file)
    if not urls:
        raise BadRequestException(message="Hàng đợi duyệt hiện không có liên kết nào để thu thập.")

    engine = CrawlerCoreEngine(base_data_dir=Path(settings.CRAWLER_DATA_DIR))
    batch_result = await engine.crawl_batch(
        urls=urls,
        max_concurrency=payload.max_concurrency,
    )

    ingest_summary_data = None
    if payload.auto_ingest:
        session_dir = Path(settings.CRAWLER_DATA_DIR) / "sessions" / batch_result.session_id
        if session_dir.exists():
            ingest_summary = await adapter.ingest_session(
                session_dir=session_dir,
                category_id=payload.category_id,
                auto_publish=payload.auto_publish,
                created_by_id=admin.id,
            )
            ingest_summary_data = ingest_summary.model_dump()

    if payload.clear_queue:
        queue_manager.clear_approved_queue(approved_file)

    return BaseResponse(
        code="QUEUE_CRAWL_COMPLETED",
        message=f"Đã hoàn thành thu thập {batch_result.successful}/{batch_result.total_urls} liên kết.",
        data={
            "session_id": batch_result.session_id,
            "total": batch_result.total_urls,
            "total_urls": batch_result.total_urls,
            "successful": batch_result.successful,
            "failed": batch_result.failed,
            "duration_seconds": batch_result.duration_seconds,
            "ingest_summary": ingest_summary_data,
        },
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


@router.get(
    "/sessions/{session_id}",
    response_model=BaseResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get detailed crawl session results and artifacts for inspection (Admin only)",
)
async def get_crawl_session_details(
    session_id: str,
    admin: AdminUserDep,
) -> BaseResponse[dict[str, Any]]:
    safe_session_id = Path(session_id).name
    session_dir = Path(settings.CRAWLER_DATA_DIR) / "sessions" / safe_session_id
    if not session_dir.exists():
        raise EntityNotFoundException(message=f"Phiên thu thập '{safe_session_id}' không tồn tại.")

    session_info_path = session_dir / "session.json"
    results_path = session_dir / "results.json"

    session_data: dict[str, Any] = {"session_id": safe_session_id}
    if session_info_path.exists():
        try:
            with open(session_info_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
        except Exception as e:
            pass

    raw_items = []
    if results_path.exists():
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                raw_items = json.load(f)
        except Exception as e:
            pass

    detailed_items = []
    for it in raw_items:
        art_dir_str = it.get("artifact_dir")
        art_dir = Path(art_dir_str) if art_dir_str else None

        pdf_list = []
        img_list = []
        markdown_content = ""
        is_meaningful = True
        has_ocr = False
        page_hash = art_dir.name if art_dir else ""
        is_ingested = False
        ingested_at = None

        if art_dir and art_dir.exists():
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
                            "url": f"/api/v1/crawler/media/{page_hash}/pdfs/{p.name}",
                        })

            imgs_dir = art_dir / "images"
            if imgs_dir.exists() and imgs_dir.is_dir():
                for img in sorted(imgs_dir.glob("*")):
                    if img.is_file():
                        img_list.append({
                            "name": img.name,
                            "size": img.stat().st_size,
                            "url": f"/api/v1/crawler/media/{page_hash}/images/{img.name}",
                        })

            content_file = art_dir / "content.md"
            if content_file.exists():
                try:
                    markdown_content = content_file.read_text(encoding="utf-8")
                except Exception:
                    markdown_content = ""

            is_meaningful = CrawlIngestionAdapter.is_meaningful_markdown(markdown_content)
            has_ocr = "## Nội dung trích xuất từ văn bản đính kèm" in markdown_content

        detailed_items.append({
            "url": it.get("url", ""),
            "title": it.get("title", ""),
            "status": it.get("status", "unknown"),
            "page_hash": page_hash,
            "duration_seconds": it.get("duration_seconds", 0),
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
