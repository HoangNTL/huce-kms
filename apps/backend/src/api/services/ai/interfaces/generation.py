from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from api.services.ai.schemas.ai import GenerationRequest, GenerationResult, StreamToken


class BaseGenerationProvider(ABC):
    """Abstract base class for all LLM generation providers (Gemini, Groq, OpenRouter)."""

    provider_name: str
    default_model: str

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """Execute text completion and return structured result."""
        pass

    @abstractmethod
    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        """Yield real-time streaming tokens for Server-Sent Events (SSE)."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verify whether required API keys / configuration are present."""
        pass
