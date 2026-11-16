import unittest
from collections.abc import AsyncGenerator

from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.interfaces.generation import BaseGenerationProvider
from api.services.ai.managers.generation_manager import GenerationManager
from api.services.ai.schemas.ai import (
    AIErrorType,
    AIProviderError,
    GenerationRequest,
    GenerationResult,
    StreamToken,
)


class MockProvider(BaseGenerationProvider):
    def __init__(
        self,
        name: str,
        fail_with: AIProviderError | None = None,
        return_text: str = "Mock answer",
    ):
        self.provider_name = name
        self.default_model = f"mock-{name}-model"
        self.fail_with = fail_with
        self.return_text = return_text
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.call_count += 1
        if self.fail_with:
            raise self.fail_with
        return GenerationResult(
            text=self.return_text,
            provider=self.provider_name,
            model=self.default_model,
        )

    async def generate_stream(
        self, request: GenerationRequest
    ) -> AsyncGenerator[StreamToken, None]:
        self.call_count += 1
        if self.fail_with:
            raise self.fail_with
        for word in self.return_text.split():
            yield StreamToken(
                content=word + " ",
                provider=self.provider_name,
                model=self.default_model,
            )


class TestGenerationManagerFallback(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        cooldown_tracker.clear_all()

    async def test_successful_primary_provider(self):
        gemini = MockProvider("gemini", return_text="Gemini Answer")
        groq = MockProvider("groq", return_text="Groq Answer")

        manager = GenerationManager(
            providers=[gemini, groq],
            provider_order=["gemini", "groq"],
        )

        res = await manager.generate(GenerationRequest(prompt="Hello HUCE"))
        self.assertEqual(res.provider, "gemini")
        self.assertEqual(res.text, "Gemini Answer")
        self.assertEqual(gemini.call_count, 1)
        self.assertEqual(groq.call_count, 0)

    async def test_fallback_on_quota_exhausted(self):
        # Gemini fails with QUOTA_EXHAUSTED
        gemini = MockProvider(
            "gemini",
            fail_with=AIProviderError(
                provider="gemini",
                error_type=AIErrorType.QUOTA_EXHAUSTED,
                message="Free tier daily limit exceeded",
            ),
        )
        groq = MockProvider("groq", return_text="Groq Fallback Answer")

        manager = GenerationManager(
            providers=[gemini, groq],
            provider_order=["gemini", "groq"],
        )

        res = await manager.generate(GenerationRequest(prompt="Explain thesis rules"))
        self.assertEqual(res.provider, "groq")
        self.assertEqual(res.text, "Groq Fallback Answer")
        self.assertEqual(gemini.call_count, 1)
        self.assertEqual(groq.call_count, 1)

        # Gemini should now be on circuit breaker cooldown
        self.assertTrue(cooldown_tracker.is_in_cooldown("gemini"))

        # Subsequent call should immediately route to Groq without calling Gemini
        res2 = await manager.generate(GenerationRequest(prompt="Second question"))
        self.assertEqual(res2.provider, "groq")
        self.assertEqual(gemini.call_count, 1)  # unchanged!
        self.assertEqual(groq.call_count, 2)

    async def test_invalid_request_fails_fast_without_fallback(self):
        gemini = MockProvider(
            "gemini",
            fail_with=AIProviderError(
                provider="gemini",
                error_type=AIErrorType.INVALID_REQUEST,
                message="Prompt violated safety guardrails",
            ),
        )
        groq = MockProvider("groq", return_text="Groq Answer")

        manager = GenerationManager(
            providers=[gemini, groq],
            provider_order=["gemini", "groq"],
        )

        with self.assertRaises(AIProviderError) as ctx:
            await manager.generate(GenerationRequest(prompt="Toxic input"))

        self.assertEqual(ctx.exception.error_type, AIErrorType.INVALID_REQUEST)
        # Groq must NOT have been called
        self.assertEqual(groq.call_count, 0)

    async def test_streaming_fallback_before_first_token(self):
        gemini = MockProvider(
            "gemini",
            fail_with=AIProviderError(
                provider="gemini",
                error_type=AIErrorType.RATE_LIMIT_429,
                message="RPM limit reached",
            ),
        )
        groq = MockProvider("groq", return_text="Streaming fallback content")

        manager = GenerationManager(
            providers=[gemini, groq],
            provider_order=["gemini", "groq"],
        )

        tokens = []
        async for tok in manager.generate_stream(GenerationRequest(prompt="Stream me")):
            tokens.append(tok.content)

        full_stream = "".join(tokens).strip()
        self.assertEqual(full_stream, "Streaming fallback content")
        self.assertEqual(groq.call_count, 1)


if __name__ == "__main__":
    unittest.main()
