from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class AIErrorType(str, Enum):
    """Categorized AI failure types for deterministic fallback logic."""

    RATE_LIMIT_429 = "rate_limit_429"      # Temporary RPM/TPM limit -> Exponential backoff retry
    QUOTA_EXHAUSTED = "quota_exhausted"    # Daily/Monthly quota exhausted -> Cooldown & fallback next provider
    SERVER_ERROR_5XX = "server_error_5xx"  # Provider internal / unavailable -> Transient retry then fallback
    TIMEOUT = "timeout"                    # Connection / read timeout -> Fallback next provider
    AUTH_ERROR_401 = "auth_error_401"      # Invalid API key / unauthorized -> Cooldown & skip
    INVALID_REQUEST = "invalid_request"    # 400 bad payload / safety block -> Fail fast, DO NOT fallback
    UNKNOWN = "unknown"


class AIProviderError(Exception):
    """Normalized exception raised by AI provider adapters."""

    def __init__(
        self,
        provider: str,
        error_type: AIErrorType,
        message: str,
        status_code: int | None = None,
        retry_after: float | None = None,
        model: str | None = None,
        raw_error: Exception | None = None,
    ):
        super().__init__(f"[{provider}:{model or 'default'}] {error_type.value}: {message}")
        self.provider = provider
        self.error_type = error_type
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        self.model = model
        self.raw_error = raw_error


class GenerationRequest(BaseModel):
    """Standardized LLM generation parameters across all providers."""

    prompt: str
    system_instruction: str | None = None
    temperature: float = 0.3
    max_tokens: int | None = 2048
    model: str | None = None


class GenerationResult(BaseModel):
    """Unified LLM output payload."""

    text: str
    provider: str
    model: str
    finish_reason: str | None = "stop"
    usage: dict[str, int] = Field(default_factory=dict)


class StreamToken(BaseModel):
    """Real-time token delta for streaming endpoints (SSE)."""

    content: str
    provider: str
    model: str
    is_final: bool = False


class EmbeddingResult(BaseModel):
    """Unified vector embedding output payload."""

    embeddings: list[list[float]]
    provider: str
    model: str
    dimension: int
