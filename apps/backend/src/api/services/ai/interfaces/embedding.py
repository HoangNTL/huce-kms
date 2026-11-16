from abc import ABC, abstractmethod
from typing import Sequence

from api.services.ai.schemas.ai import EmbeddingResult


class BaseEmbeddingProvider(ABC):
    """Abstract base class for Vector Embedding providers (Gemini, Voyage, Jina)."""

    provider_name: str
    model_name: str
    dimension: int

    @abstractmethod
    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 10
    ) -> EmbeddingResult:
        """Generate vector embeddings for a sequence of document texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> list[float]:
        """Generate vector embedding for a single user search query."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verify whether required API keys / configuration are present."""
        pass
