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

logger = logging.getLogger("huce_kms.ai.openrouter")


class OpenRouterGenerationProvider(BaseGenerationProvider):
    """OpenRouter multi-model LLM gateway adapter via OpenAI-compatible REST API."""

    provider_name: str = "openrouter"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = "deepseek/deepseek-chat",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 35.0,
    ):
        self.api_key = api_key or getattr(settings, "OPENROUTER_API_KEY", None)
        self.default_model = default_model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_messages(self, request: GenerationRequest) -> list[dict[str, str]]:
        messages = []
        if request.system_instruction:
            messages.append({"role": "system", "content": request.system_instruction})
        messages.append({"role": "user", "content": request.prompt})
        return messages

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://huce.edu.vn",
            "X-Title": "HUCE KMS Academic Assistant",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": self._build_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": False,
        }

        try:
            res = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
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
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            classified = ErrorClassifier.classify(
                self.provider_name, exc, model=model, status_code=status_code
            )
            logger.warning("[OpenRouterGenerationProvider] Failed: %s", classified)
            raise classified from exc

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        model = request.model or self.default_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://huce.edu.vn",
            "X-Title": "HUCE KMS Academic Assistant",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": self._build_messages(request),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[len("data: ") :].strip()
                        if data_str == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield StreamToken(
                                    content=content,
                                    provider=self.provider_name,
                                    model=model,
                                    is_final=False,
                                )
                        except json.JSONDecodeError:
                            continue

            yield StreamToken(
                content="",
                provider=self.provider_name,
                model=model,
                is_final=True,
            )
        except Exception as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            classified = ErrorClassifier.classify(
                self.provider_name, exc, model=model, status_code=status_code
            )
            logger.warning("[OpenRouterGenerationProvider] Streaming failed: %s", classified)
            raise classified from exc
