import logging
from typing import Sequence
import httpx

from api.core.config import settings
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.schemas.ai import EmbeddingResult

logger = logging.getLogger("huce_kms.ai.embedding.voyage")


class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """Voyage AI Vector Embedding adapter via REST API."""

    provider_name: str = "voyage"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "voyage-3-lite",
        dimension: int = 512,
        base_url: str = "https://api.voyageai.com/v1",
        timeout: float = 30.0,
    ):
        self.api_key = api_key or getattr(settings, "VOYAGE_API_KEY", None)
        self.model_name = getattr(settings, "VOYAGE_MODEL", model_name)
        self.dimension = dimension
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def embed_texts(
        self,
        texts: Sequence[str],
        batch_size: int = 20,
        input_type: str = "document",
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
                payload = {
                    "input": batch,
                    "model": self.model_name,
                    "input_type": input_type,
                }
                # If dimension is specified and supported
                if self.dimension:
                    payload["output_dimension"] = self.dimension

                try:
                    resp = await client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    items = data.get("data", [])
                    # Sort by index if provided
                    items.sort(key=lambda x: x.get("index", 0))
                    for item in items:
                        emb = item.get("embedding", [])
                        all_embeddings.append(emb)

                except Exception as exc:
                    status_code = getattr(getattr(exc, "response", None), "status_code", None)
                    classified = ErrorClassifier.classify(
                        provider=self.provider_name,
                        exc=exc,
                        model=self.model_name,
                        status_code=status_code,
                    )
                    logger.error(
                        "Voyage AI embedding batch [%d:%d] failed: %s",
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

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query], batch_size=1, input_type="query")
        if not result.embeddings:
            raise RuntimeError("Failed to obtain Voyage embedding for query.")
        return result.embeddings[0]
