import asyncio
import logging
from typing import Sequence

from api.core.config import settings
from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.fallback.error_classifier import extract_retry_delay
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.providers.embedding.gemini import GeminiEmbeddingProvider
from api.services.ai.providers.embedding.rest import (
    JinaEmbeddingProvider,
    VoyageEmbeddingProvider,
)
from api.services.ai.schemas.ai import (
    AIErrorType,
    AIProviderError,
    EmbeddingResult,
)

logger = logging.getLogger("huce_kms.ai.embedding_manager")


class EmbeddingManager:
    """
    Manages vector embeddings with strict Vector Space governance.

    Architectural Rule:
    Vector space cannot be dynamically switched during queries or indexing
    without corrupting Qdrant similarity scores. Therefore, EmbeddingManager
    enforces a Canonical Single-Model space, backed by resilient exponential
    backoff, retry-delay inspection, and circuit-breaker monitoring.
    """

    def __init__(
        self,
        active_provider: BaseEmbeddingProvider | None = None,
        canonical_provider_name: str | None = None,
        expected_dimension: int = settings.VECTOR_DIMENSION,
        max_retries: int = 5,
    ):
        self.expected_dimension = expected_dimension
        self.max_retries = max_retries
        self.canonical_name = (
            canonical_provider_name
            or getattr(settings, "EMBEDDING_PROVIDER", "gemini")
        ).lower().strip()

        # Registry of available embedding adapters
        self._providers: dict[str, BaseEmbeddingProvider] = {
            "gemini": GeminiEmbeddingProvider(dimension=self.expected_dimension),
            "voyage": VoyageEmbeddingProvider(dimension=self.expected_dimension),
            "jina": JinaEmbeddingProvider(dimension=self.expected_dimension),
        }

        if active_provider:
            self._active_provider = active_provider
            self._providers[active_provider.provider_name] = active_provider
        else:
            if self.canonical_name not in self._providers:
                raise ValueError(
                    f"Unknown canonical embedding provider '{self.canonical_name}'. "
                    f"Available: {list(self._providers.keys())}"
                )
            self._active_provider = self._providers[self.canonical_name]

        # Enforce vector space compatibility
        self._validate_dimension(self._active_provider)

    def _validate_dimension(self, provider: BaseEmbeddingProvider) -> None:
        """Ensure provider vector dimension strictly matches Qdrant collection settings."""
        if provider.dimension != self.expected_dimension:
            raise ValueError(
                f"[VECTOR SPACE MISMATCH] Active provider '{provider.provider_name}' "
                f"dimension ({provider.dimension}) does not match configured Qdrant collection "
                f"dimension ({self.expected_dimension}). Cannot safely index or query vector DB."
            )

    @property
    def active_provider(self) -> BaseEmbeddingProvider:
        return self._active_provider

    @property
    def dimension(self) -> int:
        return self.expected_dimension

    @property
    def model(self) -> str:
        return self._active_provider.model_name

    def register_provider(self, provider: BaseEmbeddingProvider) -> None:
        """Register a custom or test embedding provider."""
        self._providers[provider.provider_name] = provider

    def set_canonical_provider(self, provider_name: str) -> None:
        """Switch canonical provider (caution: requires re-indexing Qdrant)."""
        name = provider_name.lower().strip()
        if name not in self._providers:
            raise ValueError(f"Provider '{name}' not found in registered providers.")
        new_provider = self._providers[name]
        self._validate_dimension(new_provider)
        self._active_provider = new_provider
        self.canonical_name = name
        logger.info("Canonical embedding provider switched to '%s'", name)

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding vector for a single search query with resilience."""
        provider = self._active_provider
        name = provider.provider_name

        if not provider.is_available():
            raise AIProviderError(
                provider=name,
                error_type=AIErrorType.AUTH_ERROR_401,
                message=f"Embedding provider '{name}' is not configured with an API key.",
            )

        if cooldown_tracker.is_in_cooldown(name):
            remaining = cooldown_tracker.get_remaining_cooldown(name)
            raise AIProviderError(
                provider=name,
                error_type=AIErrorType.QUOTA_EXHAUSTED,
                message=f"Embedding provider '{name}' is in cooldown ({remaining:.0f}s left).",
            )

        for attempt in range(self.max_retries):
            try:
                vec = await provider.embed_query(query)
                if len(vec) != self.expected_dimension:
                    raise ValueError(
                        f"Embedding vector dimension {len(vec)} != expected {self.expected_dimension}"
                    )
                return vec
            except AIProviderError as pie:
                if pie.error_type == AIErrorType.RATE_LIMIT_429 and attempt < self.max_retries - 1:
                    wait_time = pie.retry_after or ((attempt + 1) * 3.0)
                    logger.warning(
                        "Embedding query rate limit on '%s'. Retrying in %.1fs (attempt %d/%d)...",
                        name,
                        wait_time,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(wait_time)
                    continue

                if pie.error_type == AIErrorType.QUOTA_EXHAUSTED:
                    cooldown_tracker.set_cooldown(name, duration_seconds=900, reason="Quota exhausted")
                raise

        raise AIProviderError(
            provider=name,
            error_type=AIErrorType.RATE_LIMIT_429,
            message=f"Rate limit retries exhausted for embedding provider '{name}'.",
        )

    async def embed_texts(
        self,
        texts: Sequence[str],
        batch_size: int = 10,
        pause_between_batches: float = 1.0,
    ) -> EmbeddingResult:
        """
        Embed document chunks in paced batches with automatic retry on rate limits.
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                provider=self.canonical_name,
                model=self._active_provider.model_name,
                dimension=self.expected_dimension,
            )

        provider = self._active_provider
        name = provider.provider_name

        if not provider.is_available():
            raise AIProviderError(
                provider=name,
                error_type=AIErrorType.AUTH_ERROR_401,
                message=f"Embedding provider '{name}' is not configured with an API key.",
            )

        if cooldown_tracker.is_in_cooldown(name):
            remaining = cooldown_tracker.get_remaining_cooldown(name)
            raise AIProviderError(
                provider=name,
                error_type=AIErrorType.QUOTA_EXHAUSTED,
                message=f"Embedding provider '{name}' is in cooldown ({remaining:.0f}s left).",
            )

        all_embeddings: list[list[float]] = []
        total_batches = (len(texts) + batch_size - 1) // batch_size

        for b_idx in range(0, len(texts), batch_size):
            batch = list(texts[b_idx : b_idx + batch_size])
            current_batch_num = (b_idx // batch_size) + 1

            # Pacing delay between batches to respect RPM
            if b_idx > 0 and pause_between_batches > 0:
                await asyncio.sleep(pause_between_batches)

            batch_success = False
            for attempt in range(self.max_retries):
                try:
                    result = await provider.embed_texts(batch, batch_size=len(batch))
                    for emb in result.embeddings:
                        if len(emb) != self.expected_dimension:
                            raise ValueError(
                                f"Vector dimension {len(emb)} != expected {self.expected_dimension}"
                            )
                        all_embeddings.append(emb)
                    batch_success = True
                    break

                except AIProviderError as pie:
                    if pie.error_type == AIErrorType.RATE_LIMIT_429 and attempt < self.max_retries - 1:
                        wait = pie.retry_after or ((attempt + 1) * 5.0)
                        logger.warning(
                            "Embedding rate limit on batch %d/%d (provider '%s'). Retrying in %.1fs...",
                            current_batch_num,
                            total_batches,
                            name,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if pie.error_type == AIErrorType.QUOTA_EXHAUSTED:
                        cooldown_tracker.set_cooldown(name, duration_seconds=900, reason="Quota exhausted")
                        raise

                    raise

            if not batch_success:
                raise AIProviderError(
                    provider=name,
                    error_type=AIErrorType.RATE_LIMIT_429,
                    message=f"Failed embedding batch {current_batch_num}/{total_batches} after retries.",
                )

        return EmbeddingResult(
            embeddings=all_embeddings,
            provider=name,
            model=provider.model_name,
            dimension=self.expected_dimension,
        )

    # Backward compatibility with GeminiEmbeddingService methods
    async def generate_embedding(self, text: str) -> list[float]:
        """Backward-compatible alias for embed_query."""
        return await self.embed_query(text)

    async def generate_embeddings_batch(
        self,
        texts: Sequence[str],
        batch_size: int = 10,
        pause_between_batches: float = 1.0,
    ) -> list[list[float]]:
        """Backward-compatible alias for embed_texts returning raw float lists."""
        res = await self.embed_texts(
            texts=texts,
            batch_size=batch_size,
            pause_between_batches=pause_between_batches,
        )
        return res.embeddings
