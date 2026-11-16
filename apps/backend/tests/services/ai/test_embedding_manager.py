import unittest
from typing import Sequence

from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
from api.services.ai.interfaces.embedding import BaseEmbeddingProvider
from api.services.ai.managers.embedding_manager import EmbeddingManager
from api.services.ai.schemas.ai import (
    AIErrorType,
    AIProviderError,
    EmbeddingResult,
)


class MockEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        name: str = "mock_embedder",
        dimension: int = 768,
        fail_with: AIProviderError | None = None,
    ):
        self.provider_name = name
        self.model_name = f"{name}-model"
        self.dimension = dimension
        self.fail_with = fail_with
        self.call_count = 0

    def is_available(self) -> bool:
        return True

    async def embed_texts(
        self, texts: Sequence[str], batch_size: int = 10
    ) -> EmbeddingResult:
        self.call_count += 1
        if self.fail_with:
            raise self.fail_with
        embeddings = [[0.1] * self.dimension for _ in texts]
        return EmbeddingResult(
            embeddings=embeddings,
            provider=self.provider_name,
            model=self.model_name,
            dimension=self.dimension,
        )

    async def embed_query(self, query: str) -> list[float]:
        self.call_count += 1
        if self.fail_with:
            raise self.fail_with
        return [0.1] * self.dimension


class TestEmbeddingManager(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        cooldown_tracker.clear_all()

    async def test_dimension_mismatch_raises_error(self):
        # Expected dimension is 768 (configured Qdrant space)
        # Incompatible provider with 1024 dimension must be rejected!
        incompatible_provider = MockEmbeddingProvider(
            name="jina_large",
            dimension=1024,
        )

        with self.assertRaises(ValueError) as ctx:
            EmbeddingManager(
                active_provider=incompatible_provider,
                expected_dimension=768,
            )

        self.assertIn("VECTOR SPACE MISMATCH", str(ctx.exception))

    async def test_successful_embed_and_backward_compatibility(self):
        provider = MockEmbeddingProvider("gemini", dimension=768)
        manager = EmbeddingManager(
            active_provider=provider,
            expected_dimension=768,
        )

        # 1. embed_query
        q_vec = await manager.embed_query("Query test")
        self.assertEqual(len(q_vec), 768)

        # 2. embed_texts
        res = await manager.embed_texts(["Chunk 1", "Chunk 2"])
        self.assertEqual(len(res.embeddings), 2)
        self.assertEqual(res.dimension, 768)

        # 3. Backward compatible aliases
        legacy_vec = await manager.generate_embedding("Legacy test")
        self.assertEqual(len(legacy_vec), 768)

        legacy_batch = await manager.generate_embeddings_batch(["C1", "C2", "C3"])
        self.assertEqual(len(legacy_batch), 3)

    async def test_quota_exhausted_triggers_cooldown(self):
        failing_provider = MockEmbeddingProvider(
            "gemini",
            dimension=768,
            fail_with=AIProviderError(
                provider="gemini",
                error_type=AIErrorType.QUOTA_EXHAUSTED,
                message="Resource exhausted daily limit",
            ),
        )
        manager = EmbeddingManager(
            active_provider=failing_provider,
            expected_dimension=768,
            max_retries=1,
        )

        with self.assertRaises(AIProviderError) as ctx:
            await manager.embed_query("Failing query")

        self.assertEqual(ctx.exception.error_type, AIErrorType.QUOTA_EXHAUSTED)
        self.assertTrue(cooldown_tracker.is_in_cooldown("gemini"))

        # embed_texts must also reject immediately without incrementing call count
        initial_calls = failing_provider.call_count
        with self.assertRaises(AIProviderError) as ctx2:
            await manager.embed_texts(["Chunk 1", "Chunk 2"])
        self.assertEqual(ctx2.exception.error_type, AIErrorType.QUOTA_EXHAUSTED)
        self.assertEqual(failing_provider.call_count, initial_calls)


if __name__ == "__main__":
    unittest.main()
