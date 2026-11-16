from functools import lru_cache
from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from api.schemas.common import BaseResponse
from api.schemas.rag import (
    RAGQueryRequest,
    RAGQueryResponse,
    SearchRequest,
    SearchResponse,
)
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.ai.managers.generation_manager import GenerationManager
from api.services.rag.service import RAGService
from api.services.rag.vector_store import QdrantVectorStore

router = APIRouter()


@lru_cache(maxsize=1)
def get_generation_manager() -> GenerationManager:
    return GenerationManager()


@lru_cache(maxsize=1)
def get_embedding_manager() -> EmbeddingManager:
    return EmbeddingManager()


def get_rag_service(
    embedder: Annotated[EmbeddingManager, Depends(get_embedding_manager)],
    generation_manager: Annotated[GenerationManager, Depends(get_generation_manager)],
) -> RAGService:
    vector_store = QdrantVectorStore()
    return RAGService(
        embedder=embedder,
        vector_store=vector_store,
        generation_manager=generation_manager,
    )


RAGServiceDep = Annotated[RAGService, Depends(get_rag_service)]


@router.post(
    "/search",
    response_model=BaseResponse[SearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Perform semantic vector search for document chunks",
)
async def search_documents(
    payload: SearchRequest,
    service: RAGServiceDep,
):
    results = await service.search(
        query=payload.query,
        category_id=payload.category_id,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    return BaseResponse(
        code="SEARCH_SUCCESS",
        message="Semantic search completed successfully.",
        data=SearchResponse(
            query=payload.query,
            results=results,
            total=len(results),
        ),
    )


@router.post(
    "/query",
    response_model=BaseResponse[RAGQueryResponse],
    status_code=status.HTTP_200_OK,
    summary="Ask a question and receive context-grounded AI answer with citations",
)
async def query_rag(
    payload: RAGQueryRequest,
    service: RAGServiceDep,
):
    result = await service.query(
        query=payload.query,
        category_id=payload.category_id,
        top_k=payload.top_k,
        temperature=payload.temperature,
    )
    return BaseResponse(
        code="QUERY_ANSWERED",
        message="Query processed successfully.",
        data=result,
    )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream RAG query response in real-time via Server-Sent Events (SSE)",
)
async def stream_rag(
    payload: RAGQueryRequest,
    service: RAGServiceDep,
):
    return StreamingResponse(
        service.stream_query(
            query=payload.query,
            category_id=payload.category_id,
            top_k=payload.top_k,
            temperature=payload.temperature,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
