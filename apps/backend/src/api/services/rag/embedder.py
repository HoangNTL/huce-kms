import logging

from api.core.config import settings
from api.services.ai.fallback.error_classifier import extract_retry_delay
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.ai.providers.embedding.gemini import GeminiEmbeddingProvider

logger = logging.getLogger("huce_kms.rag.embedder")


class GeminiEmbeddingService(EmbeddingManager):
    """
    Backwards-compatible wrapper around EmbeddingManager configured with Gemini.
    Maintains existing signature and methods while leveraging centralized AI architecture.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = settings.EMBEDDING_MODEL_NAME,
        dimension: int = settings.VECTOR_DIMENSION,
        max_retries: int = 5,
    ):
        gemini_provider = GeminiEmbeddingProvider(
            api_key=api_key or settings.GEMINI_API_KEY,
            model_name=model,
            dimension=dimension,
        )
        super().__init__(
            active_provider=gemini_provider,
            expected_dimension=dimension,
            max_retries=max_retries,
        )
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self.dimension = dimension
        self.max_retries = max_retries


__all__ = ["GeminiEmbeddingService", "extract_retry_delay"]
