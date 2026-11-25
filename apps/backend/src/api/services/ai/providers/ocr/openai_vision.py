import base64
import httpx

from api.core.config import settings
from api.services.ai.interfaces.ocr import BaseOCRProvider


class OpenAIVisionOCRProvider(BaseOCRProvider):
    """Shared Vision OCR adapter for OpenAI-compatible multimodal chat APIs."""

    def __init__(
        self,
        provider_name: str,
        api_key: str | None,
        default_model: str,
        base_url: str,
        timeout: float = 45.0,
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

    async def extract_text(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        allow_empty: bool = True,
    ) -> str:
        b64_img = base64.b64encode(image_bytes).decode("ascii")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        payload = {
            "model": self.default_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}},
                    ],
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }
        resp = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        choices = resp.json().get("choices", [])
        extracted = (choices[0].get("message", {}).get("content") or "").strip() if choices else ""
        if not extracted and not allow_empty:
            raise RuntimeError(f"{self.provider_name} OCR returned empty text")
        return extracted


class GroqOCRProvider(OpenAIVisionOCRProvider):
    """Groq Vision OCR adapter with automatic fallback if legacy model ID returns 404."""

    FALLBACK_MODEL = "qwen/qwen3.8-27b"

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        super().__init__(
            provider_name="groq",
            api_key=api_key or getattr(settings, "GROQ_API_KEY", None),
            default_model=default_model or settings.OCR_GROQ_MODEL,
            base_url="https://api.groq.com/openai/v1",
        )

    async def extract_text(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        allow_empty: bool = True,
    ) -> str:
        try:
            return await super().extract_text(image_bytes, mime_type, prompt, allow_empty=allow_empty)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404 and self.default_model != self.FALLBACK_MODEL:
                self.default_model = self.FALLBACK_MODEL
                return await super().extract_text(image_bytes, mime_type, prompt, allow_empty=allow_empty)
            raise


class OpenRouterOCRProvider(OpenAIVisionOCRProvider):
    """OpenRouter free/multimodal Vision OCR adapter."""

    def __init__(self, api_key: str | None = None, default_model: str | None = None):
        super().__init__(
            provider_name="openrouter",
            api_key=api_key or getattr(settings, "OPENROUTER_API_KEY", None),
            default_model=default_model or settings.OCR_OPENROUTER_MODEL,
            base_url="https://openrouter.ai/api/v1",
            extra_headers={
                "HTTP-Referer": "https://huce.edu.vn",
                "X-Title": "HUCE KMS OCR",
            },
        )
