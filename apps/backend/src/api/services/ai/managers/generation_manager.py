import asyncio
import logging
from collections.abc import AsyncGenerator

from api.core.config import settings
from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.interfaces.generation import BaseGenerationProvider
from api.services.ai.providers.generation.gemini import GeminiGenerationProvider
from api.services.ai.providers.generation.openai_compatible import (
    GroqGenerationProvider,
    OpenRouterGenerationProvider,
)
from api.services.ai.schemas.ai import (
    AIErrorType,
    AIProviderError,
    GenerationRequest,
    GenerationResult,
    StreamToken,
)

logger = logging.getLogger("huce_kms.ai.generation_manager")


class GenerationManager:
    """
    Orchestrates multi-provider LLM text generation and streaming with
    intelligent fallback, rate-limit backoff, and circuit-breaker cooldowns.
    """

    def __init__(
        self,
        providers: list[BaseGenerationProvider] | None = None,
        provider_order: list[str] | None = None,
        max_retries_per_provider: int = 2,
    ):
        self.max_retries = max_retries_per_provider
        self._provider_order = provider_order or getattr(
            settings, "GENERATION_PROVIDERS", ["gemini", "groq", "openrouter"]
        )

        # Initialize default providers if not explicitly supplied
        if providers:
            self._providers = {p.provider_name: p for p in providers}
        else:
            self._providers = {
                "gemini": GeminiGenerationProvider(),
                "groq": GroqGenerationProvider(),
                "openrouter": OpenRouterGenerationProvider(),
            }

    def register_provider(self, provider: BaseGenerationProvider) -> None:
        """Register or override a generation provider."""
        self._providers[provider.provider_name] = provider

    def get_provider(self, name: str) -> BaseGenerationProvider | None:
        """Retrieve a specific registered provider."""
        return self._providers.get(name)

    def _get_active_provider_sequence(self) -> list[BaseGenerationProvider]:
        """Return configured providers in priority order."""
        seq: list[BaseGenerationProvider] = []
        for name in self._provider_order:
            provider = self._providers.get(name.lower().strip())
            if provider:
                seq.append(provider)
        # Append any registered provider not explicitly named in provider_order
        for name, provider in self._providers.items():
            if provider not in seq:
                seq.append(provider)
        return seq

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        """
        Execute text generation across providers with automatic fallback.
        Skips cooling down or unconfigured providers.
        """
        providers = self._get_active_provider_sequence()
        last_error: Exception | None = None

        for provider in providers:
            name = provider.provider_name

            # 1. Check if configured & available
            if not provider.is_available():
                logger.debug("Generation provider '%s' is not configured (no API key). Skipping.", name)
                continue

            # 2. Check circuit breaker cooldown
            if cooldown_tracker.is_in_cooldown(name):
                remaining = cooldown_tracker.get_remaining_cooldown(name)
                logger.warning(
                    "[CIRCUIT_BREAKER] Provider '%s' is cooling down (%.0fs remaining). Trying next...",
                    name,
                    remaining,
                )
                continue

            # 3. Attempt execution with intra-provider retries
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info("Executing generation with provider '%s' (attempt %d)...", name, attempt + 1)
                    result = await provider.generate(request)
                    # Clear cooldown on success
                    cooldown_tracker.clear_cooldown(name)
                    return result

                except AIProviderError as pie:
                    last_error = pie
                    logger.warning(
                        "Provider '%s' error: type=%s, message=%s (attempt %d/%d)",
                        name,
                        pie.error_type,
                        pie.message,
                        attempt + 1,
                        self.max_retries + 1,
                    )

                    # Bad request / Prompt safety block -> FAIL FAST, DO NOT FALLBACK
                    if pie.error_type == AIErrorType.INVALID_REQUEST:
                        raise

                    # Auth error 401 -> Put long cooldown and immediately fallback
                    if pie.error_type == AIErrorType.AUTH_ERROR_401:
                        cooldown_tracker.set_cooldown(name, duration_seconds=3600, reason="Invalid API Key (401)")
                        break

                    # Daily / Resource Quota Exhausted -> Put cooldown and fallback
                    if pie.error_type == AIErrorType.QUOTA_EXHAUSTED:
                        cooldown_tracker.set_cooldown(name, duration_seconds=900, reason="Quota exhausted")
                        break

                    # Rate Limit 429 -> Retry with backoff if attempts remaining
                    if pie.error_type == AIErrorType.RATE_LIMIT_429:
                        if attempt < self.max_retries:
                            wait = pie.retry_after or ((attempt + 1) * 3.0)
                            logger.info("Rate limit 429 on '%s'. Backing off %.1fs before retry...", name, wait)
                            await asyncio.sleep(wait)
                            continue
                        else:
                            # Retries exhausted -> Cooldown short time and fallback to next provider
                            cooldown_tracker.set_cooldown(name, duration_seconds=120, reason="Rate limit retries exhausted")
                            break

                    # Server 5xx or Timeout -> Retry if attempts left, else fallback
                    if pie.error_type in (AIErrorType.SERVER_ERROR_5XX, AIErrorType.TIMEOUT):
                        if attempt < self.max_retries:
                            await asyncio.sleep(2.0 * (attempt + 1))
                            continue
                        else:
                            cooldown_tracker.set_cooldown(name, duration_seconds=60, reason=f"{pie.error_type} retries exhausted")
                            break

                    # Unknown error -> fallback
                    break

                except Exception as exc:
                    last_error = exc
                    logger.error("Unexpected error in generation provider '%s': %s", name, exc)
                    break

        # All providers failed or were unavailable
        raise AIProviderError(
            provider="generation_manager",
            error_type=AIErrorType.QUOTA_EXHAUSTED,
            message="All configured generation providers failed or are unavailable.",
            raw_error=last_error,
        )

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        """
        Execute streaming generation with automatic fallback to next provider
        if initial connection or generation fails before tokens are sent.
        """
        providers = self._get_active_provider_sequence()
        last_error: Exception | None = None

        for provider in providers:
            name = provider.provider_name

            if not provider.is_available():
                continue

            if cooldown_tracker.is_in_cooldown(name):
                continue

            yielded_any = False
            try:
                logger.info("Executing streaming generation with provider '%s'...", name)
                async for token in provider.generate_stream(request):
                    yielded_any = True
                    yield token

                # If reached end of stream successfully
                cooldown_tracker.clear_cooldown(name)
                return

            except AIProviderError as pie:
                last_error = pie
                logger.warning(
                    "Streaming provider '%s' failed (yielded_any=%s): type=%s, message=%s",
                    name,
                    yielded_any,
                    pie.error_type,
                    pie.message,
                )

                if pie.error_type == AIErrorType.AUTH_ERROR_401:
                    cooldown_tracker.set_cooldown(name, duration_seconds=3600, reason="Invalid API Key (401)")
                elif pie.error_type == AIErrorType.QUOTA_EXHAUSTED:
                    cooldown_tracker.set_cooldown(name, duration_seconds=900, reason="Quota exhausted")
                elif pie.error_type == AIErrorType.RATE_LIMIT_429:
                    cooldown_tracker.set_cooldown(name, duration_seconds=120, reason="Rate limit on streaming")

                # If tokens were already streamed to client, cannot cleanly fallback without duplications
                if yielded_any:
                    yield StreamToken(
                        content=f"\n\n[Lỗi kết nối nhà cung cấp {name}: {pie.message}]",
                        provider=name,
                        model=getattr(provider, "default_model", "unknown"),
                        is_final=True,
                    )
                    return

                # If no tokens have been sent yet, continue to NEXT provider!
                continue

            except Exception as exc:
                last_error = exc
                logger.error("Unexpected error in streaming provider '%s': %s", name, exc)
                if yielded_any:
                    yield StreamToken(
                        content=f"\n\n[Lỗi kết nối nhà cung cấp {name}: {str(exc)}]",
                        provider=name,
                        model=getattr(provider, "default_model", "unknown"),
                        is_final=True,
                    )
                    return
                continue

        # All providers exhausted without emitting any token
        raise AIProviderError(
            provider="generation_manager",
            error_type=AIErrorType.QUOTA_EXHAUSTED,
            message="All configured streaming providers failed or are unavailable.",
            raw_error=last_error,
        )
