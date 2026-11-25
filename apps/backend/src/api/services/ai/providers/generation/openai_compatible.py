import json
import logging
from collections.abc import AsyncGenerator
import httpx

from api.core.config import settings
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.generation import BaseGenerationProvider
from api.services.ai.schemas.ai import (
    GenerationRequest,
    GenerationResult,
    StreamToken,
)

logger = logging.getLogger("huce_kms.ai.openai_compatible")


class OpenAICompatibleGenerationProvider(BaseGenerationProvider):
    """Shared generation adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        provider_name: str,
        api_key: str | None,
        default_model: str,
        base_url: str,
        timeout: float = 30.0,
        extra_headers: dict[str, str] | None = None,
    ):
        self.provider_name = provider_name
        self.api_key = api_key
        self.default_model = default_model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        return headers

    def _build_payload(self, request: GenerationRequest, model: str, stream: bool) -> dict:
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})
        return {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": stream,
        }

    def _classify_error(self, exc: Exception, model: str, action: str) -> Exception:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        classified = ErrorClassifier.classify(
            self.provider_name, exc, model=model, status_code=status_code
        )
        logger.warning("[%s] %s failed: %s", self.__class__.__name__, action, classified)
        return classified

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.default_model
        try:
            res = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=self._build_payload(request, model, stream=False),
            )
            res.raise_for_status()
            data = res.json()
            choices = data.get("choices", [])
            text = choices[0].get("message", {}).get("content", "") if choices else ""
            return GenerationResult(
                text=text,
                provider=self.provider_name,
                model=model,
                finish_reason=choices[0].get("finish_reason") if choices else None,
                usage=data.get("usage", {}),
            )
        except Exception as exc:
            raise self._classify_error(exc, model, "Generate") from exc

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        model = request.model or self.default_model
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=self._build_payload(request, model, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            yield StreamToken(
                                content=content,
                                provider=self.provider_name,
                                model=model,
                                is_final=False,
                            )
                    except json.JSONDecodeError:
                        continue

            yield StreamToken(content="", provider=self.provider_name, model=model, is_final=True)
        except Exception as exc:
            raise self._classify_error(exc, model, "Streaming") from exc


class GroqGenerationProvider(OpenAICompatibleGenerationProvider):
    """Groq LLM generation adapter via OpenAI-compatible REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 30.0,
    ):
        super().__init__(
            provider_name="groq",
            api_key=api_key or getattr(settings, "GROQ_API_KEY", None),
            default_model=default_model or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
            base_url=base_url,
            timeout=timeout,
        )


class OpenRouterGenerationProvider(OpenAICompatibleGenerationProvider):
    """OpenRouter multi-model LLM gateway adapter via OpenAI-compatible REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 35.0,
    ):
        super().__init__(
            provider_name="openrouter",
            api_key=api_key or getattr(settings, "OPENROUTER_API_KEY", None),
            default_model=default_model or getattr(settings, "OPENROUTER_MODEL", "deepseek/deepseek-chat"),
            base_url=base_url,
            timeout=timeout,
            extra_headers={
                "HTTP-Referer": "https://huce.edu.vn",
                "X-Title": "HUCE KMS Academic Assistant",
            },
        )
