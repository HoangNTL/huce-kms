import time
from fastapi import APIRouter, status
from sqlalchemy import func, select

from api.core.config import settings
from api.core.dependencies import AdminUserDep, DatabaseDep
from api.models.category import Category
from api.models.document import Document
from api.models.document_chunk import DocumentChunk
from api.models.user import User
from api.schemas.common import BaseResponse
from api.schemas.dashboard import DashboardStatsResponse, ServiceStatus
from api.services.rag.vector_store import QdrantVectorStore

router = APIRouter()


@router.get(
    "/stats",
    response_model=BaseResponse[DashboardStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get overall platform statistics and service health (Admin only)",
)
async def get_dashboard_stats(
    db: DatabaseDep,
    admin: AdminUserDep,
) -> BaseResponse[DashboardStatsResponse]:
    req_start = time.perf_counter()

    # 1. Total documents
    doc_count_stmt = select(func.count(Document.id))
    doc_count = (await db.execute(doc_count_stmt)).scalar() or 0

    # 2. Total chunks
    chunk_count_stmt = select(func.count(DocumentChunk.id))
    chunk_count = (await db.execute(chunk_count_stmt)).scalar() or 0

    # 3. Total users & active users
    user_count_stmt = select(func.count(User.id))
    user_count = (await db.execute(user_count_stmt)).scalar() or 0

    active_user_stmt = select(func.count(User.id)).where(User.is_active.is_(True))
    active_user_count = (await db.execute(active_user_stmt)).scalar() or 0

    # 4. Total categories
    cat_count_stmt = select(func.count(Category.id))
    cat_count = (await db.execute(cat_count_stmt)).scalar() or 0

    # 5. Total storage & indexed documents
    storage_stmt = select(func.coalesce(func.sum(Document.file_size), 0))
    total_file_size = (await db.execute(storage_stmt)).scalar() or 0

    indexed_doc_stmt = select(func.count(Document.id)).where(func.lower(Document.status) == "indexed")
    indexed_doc_count = (await db.execute(indexed_doc_stmt)).scalar() or 0

    # 6. Service health checks with real latency measurement
    db_start = time.perf_counter()
    try:
        await db.execute(select(1))
        db_latency = (time.perf_counter() - db_start) * 1000
        db_status = ServiceStatus(
            name="PostgreSQL Database",
            status="healthy",
            latency_ms=round(db_latency, 1),
            details="Cơ sở dữ liệu quan hệ",
        )
    except Exception as e:
        db_status = ServiceStatus(
            name="PostgreSQL Database",
            status="down",
            latency_ms=None,
            details=f"Lỗi kết nối cơ sở dữ liệu: {str(e)}",
        )

    # Backend API Gateway Status
    api_latency = (time.perf_counter() - req_start) * 1000
    services: list[ServiceStatus] = [
        ServiceStatus(
            name="FastAPI Backend",
            status="healthy",
            latency_ms=round(api_latency, 1),
            details="Cổng giao tiếp API hệ thống",
        ),
        db_status,
    ]

    # Check Qdrant Vector DB status
    try:
        qdrant_start = time.perf_counter()
        qdrant_store = QdrantVectorStore()
        client = qdrant_store.get_client()
        await client.get_collections()
        qdrant_latency = (time.perf_counter() - qdrant_start) * 1000
        services.append(
            ServiceStatus(
                name="Qdrant Vector DB",
                status="healthy",
                latency_ms=round(qdrant_latency, 1),
                details="Cơ sở dữ liệu vector RAG",
            )
        )
    except Exception as e:
        services.append(
            ServiceStatus(
                name="Qdrant Vector DB",
                status="degraded",
                latency_ms=None,
                details=f"Lỗi dịch vụ vector: {str(e)}",
            )
        )

    # Check Google Gemini AI status
    gemini_key = getattr(settings, "GEMINI_API_KEY", None)
    gemini_configured = bool(gemini_key and gemini_key != "your-gemini-api-key-here")
    services.append(
        ServiceStatus(
            name="Google Gemini AI",
            status="healthy" if gemini_configured else "degraded",
            latency_ms=None,
            details="Mô hình ngôn ngữ và vector nhúng" if gemini_configured else "Chưa cấu hình API Key",
        )
    )

    stats = DashboardStatsResponse(
        total_documents=doc_count,
        total_chunks=chunk_count,
        total_users=user_count,
        active_users=active_user_count,
        total_categories=cat_count,
        total_file_size_bytes=total_file_size,
        indexed_documents=indexed_doc_count,
        services=services,
    )

    return BaseResponse(
        code="DASHBOARD_STATS_RETRIEVED",
        message="Platform dashboard statistics retrieved successfully.",
        data=stats,
    )
