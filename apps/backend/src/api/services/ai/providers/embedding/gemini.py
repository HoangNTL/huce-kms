import asyncio
import logging
from typing import Sequence
from google import genai
from google.genai import types

from api.core.config import settings
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.schemas.ai import EmbeddingResult

logger = logging.getLogger("huce_kms.ai.embedding.gemini")


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini Vector Embedding adapter using official google-genai SDK."""

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = settings.EMBEDDING_MODEL_NAME,
        dimension: int = settings.VECTOR_DIMENSION,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name
        self.dimension = dimension
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 10
    ) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                provider=self.provider_name,
                model=self.model_name,
                dimension=self.dimension,
            )

        config = types.EmbedContentConfig(output_dimensionality=self.dimension)
        all_embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = list(texts[i : i + batch_size])
            try:
                response = await self.client.aio.models.embed_content(
                    model=self.model_name,
                    contents=batch,
                    config=config,
                )
                if not response.embeddings:
                    raise RuntimeError("Gemini API returned empty embeddings list.")

                for emb in response.embeddings:
                    all_embeddings.append(list(emb.values))

            except Exception as exc:
                classified = ErrorClassifier.classify(
                    provider=self.provider_name,
                    exc=exc,
                    model=self.model_name,
                )
                logger.error(
                    "Gemini embedding batch [%d:%d] failed: %s",
                    i,
                    i + len(batch),
                    classified,
                )
                raise classified from exc

        return EmbeddingResult(
            embeddings=all_embeddings,
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
        )

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query], batch_size=1)
        if not result.embeddings:
            raise RuntimeError("Failed to obtain embedding for query.")
        return result.embeddings[0]
