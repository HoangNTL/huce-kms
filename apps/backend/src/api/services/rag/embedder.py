import asyncio
import logging
import re
from typing import Sequence
from google import genai
from google.genai import types

from api.core.config import settings
from api.core.exceptions import BadRequestException

logger = logging.getLogger("huce_kms.rag.embedder")


def extract_retry_delay(error_str: str) -> float | None:
    """Extract required retry delay in seconds from Gemini rate-limit error payload."""
    match = re.search(r"retryDelay':\s*'([0-9.]+)s'", error_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    match = re.search(r"retry in ([0-9.]+)s", error_str, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


class GeminiEmbeddingService:
    """Generates dense vector embeddings using Google Gemini Embedding API with rate-limit resilience."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = settings.EMBEDDING_MODEL_NAME,
        dimension: int = settings.VECTOR_DIMENSION,
        max_retries: int = 5,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.dimension = dimension
        self.max_retries = max_retries
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise BadRequestException(
                message="GEMINI_API_KEY is not configured. Please provide GEMINI_API_KEY in .env file."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate vector embedding for a single text string."""
        results = await self.generate_embeddings_batch([text])
        return results[0]

    async def _embed_batch_with_retry(
        self,
        batch: list[str],
        batch_index: int,
        total_batches: int,
    ) -> list[list[float]]:
        """Embed a single batch with automatic retry on 429 RESOURCE_EXHAUSTED."""
        config = types.EmbedContentConfig(output_dimensionality=self.dimension)

        for attempt in range(self.max_retries):
            try:
                response = await self.client.aio.models.embed_content(
                    model=self.model,
                    contents=batch,
                    config=config,
                )

                if not response.embeddings:
                    raise BadRequestException(
                        message="Gemini API returned no vector embeddings."
                    )

                return [list(emb.values) for emb in response.embeddings]

            except BadRequestException:
                raise
            except Exception as e:
                err_str = str(e)
                is_rate_limit = (
                    "429" in err_str
                    or "RESOURCE_EXHAUSTED" in err_str
                    or "quota" in err_str.lower()
                )

                if is_rate_limit and attempt < self.max_retries - 1:
                    delay = extract_retry_delay(err_str)
                    wait_time = delay + 1.5 if delay else (attempt + 1) * 10.0
                    logger.warning(
                        "Gemini Embedding Free Tier quota reached (429 RESOURCE_EXHAUSTED) on batch %d/%d. "
                        "Waiting %.1fs before retry (attempt %d/%d)...",
                        batch_index + 1,
                        total_batches,
                        wait_time,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Failed to generate Gemini embeddings on batch %d/%d: %s",
                        batch_index + 1,
                        total_batches,
                        e,
                    )
                    raise BadRequestException(
                        message=f"Error generating Google Gemini embeddings: {err_str}"
                    ) from e

        raise BadRequestException(
            message="Exceeded maximum retries for Gemini embedding generation."
        )

    async def generate_embeddings_batch(
        self, texts: Sequence[str], batch_size: int = 10
    ) -> list[list[float]]:
        """Generate vector embeddings for a sequence of texts in small batches with pacing."""
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        batches = [list(texts[i : i + batch_size]) for i in range(0, len(texts), batch_size)]
        total_batches = len(batches)

        for idx, batch in enumerate(batches):
            embeddings = await self._embed_batch_with_retry(batch, idx, total_batches)
            all_embeddings.extend(embeddings)

            # Small throttle between batches if more remain to respect Free Tier token/minute limit
            if idx < total_batches - 1:
                await asyncio.sleep(1.0)

        return all_embeddings
