import asyncio
import logging

from api.core.config import settings
from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.fallback.error_classifier import ErrorClassifier, extract_retry_delay
from api.services.ai.interfaces.ocr import BaseOCRProvider, OCRBlockedError
from api.services.ai.providers.ocr import (
    GeminiOCRProvider,
    GroqOCRProvider,
    OpenRouterOCRProvider,
)
from api.services.ai.schemas.ai import AIErrorType

logger = logging.getLogger("huce_kms.ai.ocr_manager")


class VisionOCRManager:
    """
    Orchestrates multi-provider Vision OCR (Gemini -> Groq -> OpenRouter)
    with automatic fallback, rate-limit backoff, and circuit-breaker cooldowns.
    """

    def __init__(
        self,
        providers: list[BaseOCRProvider] | None = None,
        provider_order: list[str] | None = None,
        max_retries_per_provider: int | None = None,
    ):
        self.max_retries = max(1, max_retries_per_provider or settings.OCR_MAX_RETRIES)
        self._provider_order = provider_order or list(settings.OCR_PROVIDERS)

        if providers is not None:
            self._providers = {p.provider_name: p for p in providers}
        else:
            self._providers = {
                "gemini": GeminiOCRProvider(),
                "groq": GroqOCRProvider(),
                "openrouter": OpenRouterOCRProvider(),
            }

    @staticmethod
    def _build_ocr_prompt(allow_empty: bool) -> str:
        empty_rule = (
            "4. Nếu hình ảnh hoàn toàn trống hoặc chỉ là ảnh phong cảnh/logo thuần túy không có văn bản, mới trả về chuỗi rỗng.\n"
            if allow_empty
            else "4. Đây là trang tài liệu văn bản, hãy trích xuất đầy đủ mọi chữ, số, bảng biểu và công thức nhìn thấy.\n"
        )
        return (
            "Bạn là hệ thống trích xuất văn bản (OCR) chính xác cao cho tài liệu học thuật và văn bản hành chính Việt Nam.\n"
            "Hãy đọc và trích xuất toàn bộ nội dung văn bản trên hình ảnh này theo đúng thứ tự đọc tự nhiên (từ trên xuống dưới, từ trái sang phải).\n"
            "Yêu cầu:\n"
            "1. Giữ nguyên cấu trúc, tiêu đề, số thứ tự, số hiệu văn bản, các Chương/Mục/Điều/Khoản/Phụ lục và giữ đầy đủ nội dung, không bỏ sót dòng nào.\n"
            "2. Không bọc các tiêu đề Chương, Mục, Điều, Phụ lục trong dấu ** hoặc # không cần thiết; giữ các dòng tiêu đề rõ ràng ở đầu dòng.\n"
            "3. Nếu có bảng biểu, hãy chuyển đổi chính xác thành định dạng Markdown Table.\n"
            f"{empty_rule}"
            "5. Chỉ trả về nội dung văn bản trích xuất được, không kèm lời mở đầu, giải thích hay bình luận."
        )

    def _get_active_provider_sequence(self) -> list[BaseOCRProvider]:
        seq: list[BaseOCRProvider] = []
        for name in self._provider_order:
            provider = self._providers.get(name.lower().strip())
            if provider:
                seq.append(provider)
        for provider in self._providers.values():
            if provider not in seq:
                seq.append(provider)
        return seq

    def has_available_provider(self) -> bool:
        """Return True if at least one Vision OCR provider is configured."""
        return any(p.is_available() for p in self._get_active_provider_sequence())

    async def ocr_image_bytes(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        semaphore: asyncio.Semaphore | None = None,
        context_label: str = "image",
        raise_on_error: bool = False,
        allow_empty: bool = True,
    ) -> str:
        """Transcribe text from image bytes across configured Vision OCR providers."""
        if not self.has_available_provider():
            logger.warning("No Vision OCR API keys configured; skipping OCR for %s.", context_label)
            return ""

        prompt = self._build_ocr_prompt(allow_empty=allow_empty)
        providers = self._get_active_provider_sequence()

        async def _run_ocr() -> str:
            last_exc: Exception | None = None

            for provider in providers:
                name = provider.provider_name
                if not provider.is_available():
                    continue

                cooldown_key = f"ocr:{name}"
                if cooldown_tracker.is_in_cooldown(cooldown_key):
                    continue

                for attempt in range(self.max_retries):
                    try:
                        extracted = await provider.extract_text(
                            image_bytes=image_bytes,
                            mime_type=mime_type,
                            prompt=prompt,
                            allow_empty=allow_empty,
                        )
                        cooldown_tracker.clear_cooldown(cooldown_key)
                        logger.info(
                            "Vision OCR (%s) processed %s (%d characters extracted).",
                            name,
                            context_label,
                            len(extracted),
                        )
                        return extracted
                    except OCRBlockedError as blocked:
                        last_exc = blocked
                        logger.warning(
                            "Vision OCR (%s) blocked on %s: %s. Falling back to next provider...",
                            name,
                            context_label,
                            blocked,
                        )
                        break
                    except Exception as exc:
                        last_exc = exc
                        resp_obj = getattr(exc, "response", None)
                        status_code = getattr(resp_obj, "status_code", None)
                        resp_snippet = ""
                        if resp_obj is not None:
                            try:
                                resp_snippet = (resp_obj.text or "").strip()[:300]
                            except Exception:
                                resp_snippet = ""

                        classified = ErrorClassifier.classify(
                            provider=name,
                            exc=exc,
                            model=getattr(provider, "default_model", None),
                            status_code=status_code,
                        )
                        if classified.error_type == AIErrorType.AUTH_ERROR_401:
                            cooldown_tracker.set_cooldown(cooldown_key, 3600, "Invalid API key")
                            break
                        if status_code in (404, 410):
                            logger.warning(
                                "Vision OCR (%s) model/endpoint unavailable (HTTP %s: %s). Cooling down provider...",
                                name,
                                status_code,
                                resp_snippet or exc,
                            )
                            cooldown_tracker.set_cooldown(
                                cooldown_key,
                                settings.PROVIDER_COOLDOWN_SECONDS,
                                f"HTTP {status_code} model/endpoint unavailable",
                            )
                            break
                        if classified.error_type == AIErrorType.QUOTA_EXHAUSTED:
                            cooldown_tracker.set_cooldown(cooldown_key, 300, "Quota exhausted")
                            break
                        if classified.error_type == AIErrorType.INVALID_REQUEST:
                            logger.warning(
                                "Vision OCR (%s) rejected payload on %s (%s). Falling back...",
                                name,
                                context_label,
                                resp_snippet or classified.message,
                            )
                            if "cannot be relayed" in (resp_snippet or str(exc)).lower():
                                cooldown_tracker.set_cooldown(cooldown_key, 300, "Provider relay/routing error")
                            break

                        if cooldown_tracker.is_in_cooldown(cooldown_key):
                            break

                        if attempt < self.max_retries - 1:
                            hinted_delay = extract_retry_delay(str(exc))
                            wait_seconds = min(20.0, max(3.0 * (attempt + 1), hinted_delay or 0.0))
                            logger.warning(
                                "Vision OCR (%s) attempt %d/%d failed on %s: %s. Retrying in %.1fs...",
                                name,
                                attempt + 1,
                                self.max_retries,
                                context_label,
                                resp_snippet or exc,
                                wait_seconds,
                            )
                            await asyncio.sleep(wait_seconds)
                        else:
                            logger.warning(
                                "Vision OCR (%s) exhausted retries on %s: %s. Trying next provider...",
                                name,
                                context_label,
                                resp_snippet or exc,
                            )

            if raise_on_error and last_exc is not None:
                raise last_exc
            return ""

        if semaphore:
            async with semaphore:
                return await _run_ocr()
        return await _run_ocr()

    async def ocr_images_batch(
        self,
        items: list[tuple[str, bytes]],
        mime_type: str = "image/png",
        max_concurrency: int | None = None,
        raise_on_error: bool = True,
        allow_empty: bool = False,
    ) -> list[str | Exception]:
        """Run OCR concurrently over labeled image bytes."""
        concurrency = max(1, max_concurrency or settings.OCR_MAX_CONCURRENCY)
        semaphore = asyncio.Semaphore(concurrency)
        tasks = [
            self.ocr_image_bytes(
                image_bytes=img_bytes,
                mime_type=mime_type,
                semaphore=semaphore,
                context_label=label,
                raise_on_error=raise_on_error,
                allow_empty=allow_empty,
            )
            for label, img_bytes in items
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)


ocr_manager = VisionOCRManager()
