import logging

from google import genai
from google.genai import types

from api.core.config import settings
from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.interfaces.ocr import BaseOCRProvider, OCRBlockedError

logger = logging.getLogger("huce_kms.ai.ocr_gemini")

# Prioritized Gemini/Gemma Vision models verified on generativelanguage v1
_GEMINI_VISION_FALLBACK_CHAIN = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
    "gemini-3.6-flash",
    "gemini-3.8-flash",
)


class GeminiOCRProvider(BaseOCRProvider):
    """Google Gemini Vision OCR adapter with automatic secondary Gemini model fallback."""

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        fallback_model: str | None = None,
        client: genai.Client | None = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.default_model = default_model or settings.OCR_GEMINI_MODEL or settings.LLM_MODEL
        self.fallback_model = (
            fallback_model if fallback_model is not None else settings.OCR_GEMINI_FALLBACK_MODEL
        )
        self._client = client

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not configured.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _candidate_models(self) -> list[str]:
        candidates: list[str] = []
        for model in (
            self.default_model,
            self.fallback_model,
            *_GEMINI_VISION_FALLBACK_CHAIN,
            settings.LLM_MODEL,
        ):
            if model and model not in candidates:
                candidates.append(model)
        non_dead = [
            m
            for m in candidates
            if not cooldown_tracker.is_in_cooldown(f"ocr:gemini:dead:{m}")
            and not cooldown_tracker.is_in_cooldown(f"ocr:gemini:model:{m}")
        ]
        pool = non_dead or candidates
        fresh = [m for m in pool if not cooldown_tracker.is_in_cooldown(f"ocr:gemini:busy:{m}")]
        return fresh or pool

    async def _extract_with_model(
        self,
        model_name: str,
        part: types.Part,
        prompt: str,
        allow_empty: bool,
    ) -> str:
        response = await self.client.aio.models.generate_content(
            model=model_name,
            contents=[part, prompt],
        )
        extracted = response.text.strip() if response.text else ""
        if not extracted and not allow_empty:
            candidates = getattr(response, "candidates", None) or []
            finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
            reason_str = str(finish_reason or "").upper()
            if any(flag in reason_str for flag in ("RECITATION", "SAFETY", "PROHIBITED", "BLOCKLIST")):
                raise OCRBlockedError(f"Gemini ({model_name}) blocked OCR output (finish_reason={finish_reason})")
            raise RuntimeError(f"Gemini ({model_name}) OCR returned empty text (finish_reason={finish_reason})")
        return extracted

    async def extract_text(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        allow_empty: bool = True,
    ) -> str:
        part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        models = self._candidate_models()
        last_exc: Exception | None = None
        last_transient_exc: Exception | None = None

        for idx, model_name in enumerate(models):
            effective_prompt = prompt
            if idx > 0 and isinstance(last_exc, OCRBlockedError):
                effective_prompt = (
                    f"{prompt}\nHãy chuyển thể đầy đủ nội dung trang văn bản thành ghi chú có cấu trúc rõ ràng (Markdown)."
                )
            try:
                return await self._extract_with_model(
                    model_name=model_name,
                    part=part,
                    prompt=effective_prompt,
                    allow_empty=allow_empty,
                )
            except OCRBlockedError as blocked:
                last_exc = blocked
                if idx < len(models) - 1:
                    logger.warning(
                        "%s. Retrying with fallback Gemini model %s...",
                        blocked,
                        models[idx + 1],
                    )
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                err_upper = str(exc).upper()
                is_daily_exhausted = "PERDAY" in err_upper or "PER DAY" in err_upper
                is_retired = is_daily_exhausted or any(
                    m in err_upper for m in ("404", "NOT_FOUND", "NO LONGER AVAILABLE")
                )
                is_overloaded = not is_daily_exhausted and any(
                    m in err_upper for m in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
                )
                if is_retired:
                    reason = "Daily quota exhausted" if is_daily_exhausted else "Model retired/404"
                    cooldown_tracker.set_cooldown(f"ocr:gemini:dead:{model_name}", 3600, reason)
                elif is_overloaded:
                    last_transient_exc = exc
                    cooldown_tracker.set_cooldown(f"ocr:gemini:busy:{model_name}", 15, "Model 429/503 transient")

                if (is_retired or is_overloaded) and idx < len(models) - 1:
                    logger.warning(
                        "Gemini model %s unavailable (%s). Switching to fallback Gemini model %s...",
                        model_name,
                        exc,
                        models[idx + 1],
                    )
                    continue
                if all(
                    cooldown_tracker.is_in_cooldown(f"ocr:gemini:busy:{m}")
                    or cooldown_tracker.is_in_cooldown(f"ocr:gemini:dead:{m}")
                    for m in models
                ):
                    cooldown_tracker.set_cooldown(
                        "ocr:gemini", 15, "All Gemini vision models overloaded/unavailable"
                    )
                if is_retired and last_transient_exc is not None:
                    raise last_transient_exc from exc
                raise

        if last_transient_exc is not None:
            raise last_transient_exc
        if last_exc is not None:
            raise last_exc
        return ""
