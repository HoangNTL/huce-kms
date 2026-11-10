import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from google import genai
from google.genai import types

from api.core.config import settings
from api.core.exceptions import BadRequestException
from api.schemas.rag import (
    CitationSource,
    RAGQueryResponse,
    SearchResultItem,
)
from api.services.rag.embedder import GeminiEmbeddingService
from api.services.rag.vector_store import QdrantVectorStore

logger = logging.getLogger("huce_kms.rag.service")

HUCE_SYSTEM_INSTRUCTION = """You are an intelligent, authoritative AI assistant for Hanoi University of Civil Engineering (HUCE - Trường Đại học Xây dựng Hà Nội).
Your role is to assist students, faculty, and staff by answering questions about university regulations, academic guidelines, graduation thesis processes, scholarships, tuition fees, and administrative procedures.

Strict Guidelines:
1. Base your answer strictly on the provided Context excerpts.
2. If the context does not contain enough information to answer the question accurately, state clearly and politely that the current university documents do not contain this information. Do not fabricate, hallucinate, or assume institutional policies.
3. Reference the relevant document titles and page numbers when explaining rules, criteria, or steps.
4. Respond in the same language as the user query (if the query is in Vietnamese, reply in natural, clear, professional Vietnamese; if in English, reply in English).
5. Format your answers clearly using markdown (bullet points, bold text for key terms)."""


class RAGService:
    """Orchestrates semantic retrieval, prompt augmentation, and Gemini generative QA."""

    def __init__(
        self,
        embedder: GeminiEmbeddingService,
        vector_store: QdrantVectorStore,
        llm_model: str = settings.LLM_MODEL,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.llm_model = llm_model
        self._llm_client: genai.Client | None = None

    @property
    def llm_client(self) -> genai.Client:
        """Get or initialize the Google GenAI client for LLM generation."""
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            raise BadRequestException(
                message="GEMINI_API_KEY is not configured. Please provide GEMINI_API_KEY in .env file."
            )
        if self._llm_client is None:
            self._llm_client = genai.Client(api_key=api_key)
        return self._llm_client

    async def search(
        self,
        query: str,
        category_id: int | None = None,
        top_k: int = 5,
        score_threshold: float | None = 0.4,
    ) -> list[SearchResultItem]:
        """Perform semantic vector search against Qdrant knowledge base."""
        # 1. Generate query embedding vector
        query_vector = await self.embedder.generate_embedding(query)

        # 2. Retrieve nearest vector points from Qdrant
        raw_results = await self.vector_store.search(
            query_vector=query_vector,
            limit=top_k,
            category_id=category_id,
        )

        items: list[SearchResultItem] = []
        for pt in raw_results:
            score = float(pt["score"])
            if score_threshold is not None and score < score_threshold:
                continue

            payload = pt.get("payload", {})
            items.append(
                SearchResultItem(
                    id=pt["id"],
                    document_id=int(payload.get("document_id", 0)),
                    title=str(payload.get("title", "")),
                    category_id=payload.get("category_id"),
                    page_number=int(payload.get("page_number", 1)),
                    chunk_index=int(payload.get("chunk_index", 0)),
                    score=score,
                    content=str(payload.get("content", "")),
                )
            )

        return items

    def _build_context_and_sources(
        self, chunks: list[SearchResultItem]
    ) -> tuple[str, list[CitationSource]]:
        """Construct formatted context text and structured citation sources from search results."""
        context_parts: list[str] = []
        sources: list[CitationSource] = []

        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Excerpt {idx}] Document: \"{chunk.title}\" | Page: {chunk.page_number}\n{chunk.content}"
            )
            # Create snippet preview (first 200 chars)
            snippet = chunk.content[:200] + ("..." if len(chunk.content) > 200 else "")
            sources.append(
                CitationSource(
                    document_id=chunk.document_id,
                    title=chunk.title,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    score=chunk.score,
                    snippet=snippet,
                )
            )

        context_str = "\n\n---\n\n".join(context_parts)
        return context_str, sources

    async def query(
        self,
        query: str,
        category_id: int | None = None,
        top_k: int = 5,
        temperature: float = 0.3,
    ) -> RAGQueryResponse:
        """Execute RAG question-answering with context retrieval and Gemini LLM synthesis."""
        # 1. Retrieve relevant knowledge chunks
        chunks = await self.search(
            query=query,
            category_id=category_id,
            top_k=top_k,
            score_threshold=0.35,
        )

        # 2. Handle case where no relevant context is found in knowledge base
        if not chunks:
            fallback_message = (
                "Hiện tại hệ thống cơ sở tri thức chưa có tài liệu quy định liên quan đến câu hỏi của bạn. "
                "Vui lòng liên hệ Phòng Đào tạo hoặc Bộ phận Công tác sinh viên HUCE để được hướng dẫn chi tiết."
            )
            return RAGQueryResponse(
                query=query,
                answer=fallback_message,
                sources=[],
                total_sources=0,
            )

        # 3. Build augmented prompt
        context_str, sources = self._build_context_and_sources(chunks)
        augmented_prompt = f"User Question: {query}\n\nInstitutional Context Excerpts:\n{context_str}\n\nPlease provide a clear, accurate answer referencing the documents above."

        # 4. Generate answer via Google Gemini API with retry for transient 429/503 errors
        config = types.GenerateContentConfig(
            system_instruction=HUCE_SYSTEM_INSTRUCTION,
            temperature=temperature,
        )

        for attempt in range(3):
            try:
                response = await self.llm_client.aio.models.generate_content(
                    model=self.llm_model,
                    contents=augmented_prompt,
                    config=config,
                )

                answer_text = response.text or "Unable to generate an answer from the provided context."

                return RAGQueryResponse(
                    query=query,
                    answer=answer_text,
                    sources=sources,
                    total_sources=len(sources),
                )
            except Exception as e:
                err_str = str(e)
                is_transient = any(
                    code in err_str
                    for code in ["429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]
                )
                if is_transient and attempt < 2:
                    wait_time = (attempt + 1) * 3.0
                    logger.warning(
                        "Gemini generation transient error on attempt %d/3 (%s). Retrying in %.1fs...",
                        attempt + 1,
                        err_str,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error("Gemini text generation failed: %s", e)
                    raise BadRequestException(
                        message=f"Error generating answer via Google Gemini: {str(e)}"
                    ) from e

    async def stream_query(
        self,
        query: str,
        category_id: int | None = None,
        top_k: int = 5,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """Execute RAG query yielding Server-Sent Events (SSE) tokens for real-time chat streaming."""
        # 1. Retrieve relevant knowledge chunks
        chunks = await self.search(
            query=query,
            category_id=category_id,
            top_k=top_k,
            score_threshold=0.35,
        )

        if not chunks:
            fallback_text = (
                "Hiện tại hệ thống cơ sở tri thức chưa có tài liệu quy định liên quan đến câu hỏi của bạn. "
                "Vui lòng liên hệ Phòng Đào tạo hoặc Bộ phận Công tác sinh viên HUCE để được hỗ trợ."
            )
            yield f"data: {json.dumps({'type': 'token', 'content': fallback_text}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': []}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
            return

        context_str, sources = self._build_context_and_sources(chunks)
        augmented_prompt = f"User Question: {query}\n\nInstitutional Context Excerpts:\n{context_str}\n\nPlease provide a clear, accurate answer referencing the documents above."

        try:
            config = types.GenerateContentConfig(
                system_instruction=HUCE_SYSTEM_INSTRUCTION,
                temperature=temperature,
            )
            response_stream = await self.llm_client.aio.models.generate_content_stream(
                model=self.llm_model,
                contents=augmented_prompt,
                config=config,
            )

            async for chunk in response_stream:
                if chunk.text:
                    payload = {"type": "token", "content": chunk.text}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # Send citation sources at stream end
            sources_payload = {
                "type": "sources",
                "sources": [s.model_dump() for s in sources],
            }
            yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Gemini streaming generation failed: %s", e)
            error_payload = {"type": "error", "message": f"Streaming failed: {str(e)}"}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    @classmethod
    def assemble_retrieval_preview(
        cls,
        query: str,
        chunks: list[SearchResultItem],
    ) -> "RetrievalPreviewResponse":
        """Assemble structured retrieval preview and prompt string from search chunks."""
        from api.schemas.rag_preview import (
            RetrievalPreviewItem,
            RetrievalPreviewResponse,
        )

        context_parts = []
        for idx, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Excerpt {idx}] Document: \"{chunk.title}\" | Page: {chunk.page_number}\n{chunk.content}"
            )
        context_str = "\n\n---\n\n".join(context_parts)

        assembled_prompt = (
            f"=== SYSTEM INSTRUCTION ===\n{HUCE_SYSTEM_INSTRUCTION}\n\n"
            f"=== USER QUERY ===\n{query}\n\n"
            f"=== ASSEMBLED INSTITUTIONAL CONTEXT ({len(chunks)} chunks) ===\n{context_str or '(No matching chunks found)'}"
        )

        retrieved_items = [
            RetrievalPreviewItem(
                rank=idx,
                score=c.score,
                document_id=c.document_id,
                title=c.title,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                content_excerpt=c.content[:250] + ("..." if len(c.content) > 250 else ""),
            )
            for idx, c in enumerate(chunks, 1)
        ]

        return RetrievalPreviewResponse(
            query=query,
            total_found=len(retrieved_items),
            retrieved_chunks=retrieved_items,
            assembled_prompt_preview=assembled_prompt,
        )

    async def preview_retrieval(
        self,
        query: str,
        category_id: int | None = None,
        top_k: int = 5,
        score_threshold: float | None = 0.35,
    ) -> "RetrievalPreviewResponse":
        """
        Preview vector retrieval results and the final assembled prompt
        without executing an LLM synthesis call.
        """
        chunks = await self.search(
            query=query,
            category_id=category_id,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        return self.assemble_retrieval_preview(query=query, chunks=chunks)
