import logging
from collections.abc import AsyncGenerator
from google import genai
from google.genai import types

from api.core.config import settings
from api.services.ai.fallback.error_classifier import ErrorClassifier
from api.services.ai.interfaces.generation import BaseGenerationProvider
from api.services.ai.schemas.ai import (
    GenerationRequest,
    GenerationResult,
    StreamToken,
)

logger = logging.getLogger("huce_kms.ai.gemini")


class GeminiGenerationProvider(BaseGenerationProvider):
    """Google Gemini generation adapter using google-genai SDK."""

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = settings.LLM_MODEL,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.default_model = default_model
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

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        model = request.model or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=model,
                contents=request.prompt,
                config=config,
            )

            text = response.text or ""
            return GenerationResult(
                text=text,
                provider=self.provider_name,
                model=model,
                finish_reason="stop",
            )
        except Exception as exc:
            classified = ErrorClassifier.classify(self.provider_name, exc, model=model)
            logger.warning("[GeminiGenerationProvider] Failed: %s", classified)
            raise classified from exc

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        model = request.model or self.default_model
        config = types.GenerateContentConfig(
            system_instruction=request.system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        try:
            stream = await self.client.aio.models.generate_content_stream(
                model=model,
                contents=request.prompt,
                config=config,
            )

            async for chunk in stream:
                if chunk.text:
                    yield StreamToken(
                        content=chunk.text,
                        provider=self.provider_name,
                        model=model,
                        is_final=False,
                    )

            yield StreamToken(
                content="",
                provider=self.provider_name,
                model=model,
                is_final=True,
            )
        except Exception as exc:
            classified = ErrorClassifier.classify(self.provider_name, exc, model=model)
            logger.warning("[GeminiGenerationProvider] Streaming failed: %s", classified)
            raise classified from exc
