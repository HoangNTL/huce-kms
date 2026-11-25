from abc import ABC, abstractmethod


class OCRBlockedError(Exception):
    """Raised when an OCR provider blocks output (e.g. RECITATION/SAFETY) and should fall back."""


class BaseOCRProvider(ABC):
    """Abstract base class for Vision OCR providers (Gemini, Groq, OpenRouter)."""

    provider_name: str
    default_model: str

    @abstractmethod
    def is_available(self) -> bool:
        """Verify whether required API keys / configuration are present."""

    @abstractmethod
    async def extract_text(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        allow_empty: bool = True,
    ) -> str:
        """Transcribe text from image bytes."""
