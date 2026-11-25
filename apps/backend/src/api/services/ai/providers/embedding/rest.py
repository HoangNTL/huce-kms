import logging
from typing import Any, Sequence
import httpx

from api.core.config import settings
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.schemas.ai import EmbeddingResult

logger = logging.getLogger("huce_kms.ai.embedding.rest")


class BaseRestEmbeddingProvider(BaseEmbeddingProvider):
    """Shared REST client base for OpenAI-style /embeddings APIs (Jina, Voyage)."""

    def __init__(
        self,
        provider_name: str,
        api_key: str | None,
        model_name: str,
        dimension: int,
        base_url: str,
        timeout: float = 30.0,
    ):
        self.provider_name = provider_name
        self.api_key = api_key
        self.model_name = model_name
        self.dimension = dimension
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_payload(self, batch: list[str], purpose: str) -> dict[str, Any]:
        raise NotImplementedError

    async def _request_embeddings(
        self,
        texts: Sequence[str],
        batch_size: int,
        purpose: str,
    ) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(0, len(texts), batch_size):
                batch = list(texts[i : i + batch_size])
                try:
                    resp = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=self._build_payload(batch, purpose),
                    )
                    resp.raise_for_status()
                    items = resp.json().get("data", [])
                    items.sort(key=lambda x: x.get("index", 0))
                    all_embeddings.extend(item.get("embedding", []) for item in items)
                except Exception as exc:
                    status_code = getattr(getattr(exc, "response", None), "status_code", None)
                    classified = ErrorClassifier.classify(
                        provider=self.provider_name,
                        exc=exc,
                        model=self.model_name,
                        status_code=status_code,
                    )
                    logger.error(
                        "%s embedding batch [%d:%d] failed: %s",
                        self.provider_name,
                        i,
                        i + len(batch),
                        classified,
                    )
                    raise classified from exc

        actual_dim = len(all_embeddings[0]) if all_embeddings else self.dimension
        return EmbeddingResult(
            embeddings=all_embeddings,
            provider=self.provider_name,
            model=self.model_name,
            dimension=actual_dim,
        )


class JinaEmbeddingProvider(BaseRestEmbeddingProvider):
    """Jina AI Vector Embedding adapter via REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "jina-embeddings-v3",
        dimension: int = 1024,
        base_url: str = "https://api.jina.ai/v1",
        timeout: float = 30.0,
    ):
        super().__init__(
            provider_name="jina",
            api_key=api_key or getattr(settings, "JINA_API_KEY", None),
            model_name=getattr(settings, "JINA_MODEL", model_name),
            dimension=dimension,
            base_url=base_url,
            timeout=timeout,
        )

    def _build_payload(self, batch: list[str], purpose: str) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "task": purpose,
            "dimensions": self.dimension,
            "input": batch,
        }

    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 16, task: str = "retrieval.passage"
    ) -> EmbeddingResult:
        return await self._request_embeddings(texts, batch_size=batch_size, purpose=task)

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query], batch_size=1, task="retrieval.query")
        if not result.embeddings:
            raise RuntimeError("Failed to obtain Jina embedding for query.")
        return result.embeddings[0]


class VoyageEmbeddingProvider(BaseRestEmbeddingProvider):
    """Voyage AI Vector Embedding adapter via REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "voyage-3-lite",
        dimension: int = 512,
        base_url: str = "https://api.voyageai.com/v1",
        timeout: float = 30.0,
    ):
        super().__init__(
            provider_name="voyage",
            api_key=api_key or getattr(settings, "VOYAGE_API_KEY", None),
            model_name=getattr(settings, "VOYAGE_MODEL", model_name),
            dimension=dimension,
            base_url=base_url,
            timeout=timeout,
        )

    def _build_payload(self, batch: list[str], purpose: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "input": batch,
            "model": self.model_name,
            "input_type": purpose,
        }
        if self.dimension:
            payload["output_dimension"] = self.dimension
        return payload

    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 20, input_type: str = "document"
    ) -> EmbeddingResult:
        return await self._request_embeddings(texts, batch_size=batch_size, purpose=input_type)

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query], batch_size=1, input_type="query")
        if not result.embeddings:
            raise RuntimeError("Failed to obtain Voyage embedding for query.")
        return result.embeddings[0]
