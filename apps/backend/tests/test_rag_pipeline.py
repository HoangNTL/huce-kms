import unittest

from api.core.exceptions import BadRequestException
from api.services.rag.chunker import TextChunker
from api.services.rag.parser import DocumentParser


class TestDocumentParser(unittest.TestCase):
    """Unit tests for DocumentParser text extraction logic."""

    def test_extract_plain_text_utf8(self):
        content = "Trường Đại học Xây dựng Hà Nội (HUCE)\n\nQuy chế đào tạo đại học năm 2026."
        file_bytes = content.encode("utf-8")
        pages = DocumentParser.extract_text_from_plain_text(file_bytes)

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["page_number"], 1)
        self.assertIn("HUCE", str(pages[0]["text"]))

    def test_extract_plain_text_latin1_fallback(self):
        content = "HUCE Academic Regulations - Special chars: éèà."
        file_bytes = content.encode("latin-1")
        pages = DocumentParser.extract_text_from_plain_text(file_bytes)

        self.assertEqual(len(pages), 1)
        self.assertIn("HUCE", str(pages[0]["text"]))

    def test_extract_pdf_invalid_bytes_raises_bad_request(self):
        corrupt_bytes = b"not a valid pdf header at all"
        with self.assertRaises(BadRequestException):
            DocumentParser.extract_text_from_pdf(corrupt_bytes)

    def test_extract_pdf_scanned_without_text_raises_bad_request(self):
        import pymupdf
        doc = pymupdf.open()
        doc.new_page()  # blank page without text
        pdf_bytes = doc.tobytes()
        doc.close()

        with self.assertRaises(BadRequestException) as ctx:
            DocumentParser.extract_text_from_pdf(pdf_bytes)
        self.assertIn("scan", str(ctx.exception.message).lower())

    def test_render_page_for_ocr_jpeg_and_blank_skip(self):
        import pymupdf

        doc = pymupdf.open()
        doc.new_page()
        non_blank = doc.new_page()
        non_blank.draw_rect((50, 50, 400, 200), fill=(0, 0, 0))
        pdf_bytes = doc.tobytes()
        doc.close()

        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as reloaded:
            self.assertIsNone(DocumentParser._render_page_for_ocr(reloaded[0]))
            img_bytes = DocumentParser._render_page_for_ocr(reloaded[1])

        self.assertIsNotNone(img_bytes)
        self.assertTrue(img_bytes.startswith(b"\xff\xd8"))

    def test_gemini_ocr_switches_candidate_model_on_404(self):
        from types import SimpleNamespace
        from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
        from api.services.ai.providers.ocr.gemini import GeminiOCRProvider

        cooldown_tracker.clear_all()
        called_models: list[str] = []

        async def _fake_generate(model: str, contents):
            called_models.append(model)
            if model in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
                raise RuntimeError("404 NOT_FOUND: This model is no longer available")
            return SimpleNamespace(text="Điều 1. Quy định chung", candidates=[])

        mock_client = SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(generate_content=_fake_generate))
        )
        provider = GeminiOCRProvider(
            api_key="test-key",
            default_model="gemini-2.5-flash",
            fallback_model="gemini-2.5-flash-lite",
            client=mock_client,
        )
        for _ in range(2):
            coro = provider.extract_text(b"fake-jpg", "image/jpeg", "OCR", allow_empty=False)
            try:
                coro.send(None)
                self.fail("Expected StopIteration from synchronous coroutine")
            except StopIteration as stop:
                res = stop.value
            finally:
                coro.close()
            self.assertEqual(res, "Điều 1. Quy định chung")

        # 2nd call skips 404-retired models cached in cooldown_tracker and goes straight to gemini-3.5-flash-lite
        self.assertEqual(
            called_models,
            ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash-lite"],
        )

    def test_gemini_ocr_prefers_transient_503_over_trailing_404(self):
        from types import SimpleNamespace
        from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
        from api.services.ai.providers.ocr.gemini import GeminiOCRProvider

        cooldown_tracker.clear_all()

        async def _fake_generate(model: str, contents):
            if model == "gemini-3.8-flash":
                raise RuntimeError("404 NOT_FOUND: model retired")
            raise RuntimeError("503 UNAVAILABLE: spike in demand")

        mock_client = SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(generate_content=_fake_generate))
        )
        provider = GeminiOCRProvider(
            api_key="test-key",
            default_model="gemini-3.5-flash-lite",
            fallback_model="gemini-3.1-flash-lite",
            client=mock_client,
        )
        coro = provider.extract_text(b"fake-jpg", "image/jpeg", "OCR", allow_empty=False)
        with self.assertRaises(RuntimeError) as ctx:
            try:
                coro.send(None)
            finally:
                coro.close()
        self.assertIn("503", str(ctx.exception))

    def test_ocr_checkpoint_cache_reuses_completed_pages_on_retry(self):
        from unittest.mock import patch
        import pymupdf

        doc = pymupdf.open()
        doc.new_page()
        doc.new_page()
        pdf_bytes = doc.tobytes()
        doc.close()

        class FakeMemoryStorage:
            def __init__(self):
                self.files: dict[str, bytes] = {}

            async def get_file(self, object_name: str) -> bytes:
                if object_name not in self.files:
                    raise FileNotFoundError(object_name)
                return self.files[object_name]

            async def upload_file(self, file_bytes: bytes, object_name: str, content_type: str = "") -> str:
                self.files[object_name] = file_bytes
                return object_name

        storage = FakeMemoryStorage()
        ocr_calls: list[list[str]] = []

        async def _fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        async def _fake_ocr_batch(items, mime_type="image/jpeg"):
            labels = [lbl for lbl, _ in items]
            ocr_calls.append(labels)
            if len(ocr_calls) == 1:
                return ["Nội dung trang 1", RuntimeError("503 UNAVAILABLE")]
            return ["Nội dung trang 2"]

        def _step(coro):
            try:
                coro.send(None)
                self.fail("Expected StopIteration")
            except StopIteration as stop:
                return stop.value
            finally:
                coro.close()

        with (
            patch("api.services.rag.parser.ocr_manager.has_available_provider", return_value=True),
            patch("api.services.rag.parser.DocumentParser._render_page_for_ocr", return_value=b"fake-jpg"),
            patch("api.services.rag.parser.asyncio.to_thread", side_effect=_fake_to_thread),
            patch("api.services.rag.parser.ocr_manager.ocr_images_batch", side_effect=_fake_ocr_batch),
        ):
            # Attempt 1: page 1 succeeds, page 2 fails -> raises BadRequestException but saves page 1
            with self.assertRaises(BadRequestException) as ctx:
                _step(
                    DocumentParser.extract_text_from_pdf_async(
                        pdf_bytes, enable_ocr=True, ocr_cache_key="abc123", storage_service=storage
                    )
                )
            self.assertIn("trang 2", ctx.exception.message.lower())
            self.assertIn("ocr-cache/abc123.json", storage.files)

            # Attempt 2: only page 2 is sent to OCR; page 1 comes straight from cache
            pages = _step(
                DocumentParser.extract_text_from_pdf_async(
                    pdf_bytes, enable_ocr=True, ocr_cache_key="abc123", storage_service=storage
                )
            )

        self.assertEqual(ocr_calls, [["PDF page 1", "PDF page 2"], ["PDF page 2"]])
        self.assertEqual(
            pages,
            [
                {"page_number": 1, "text": "Nội dung trang 1"},
                {"page_number": 2, "text": "Nội dung trang 2"},
            ],
        )

    @staticmethod
    def _step_sync(coro):
        try:
            while True:
                coro.send(None)
        except StopIteration as stop:
            return stop.value
        finally:
            coro.close()

    def test_raw_document_route_and_storage_reject_sensitive_paths(self):
        from unittest.mock import AsyncMock
        from api.services.storage import StorageService
        from api.v1.routes.documents import get_raw_document_file

        mock_storage = AsyncMock()
        for bad_key in (".env", "ocr-cache/abc.json", "documents/../.env"):
            with self.assertRaises(BadRequestException):
                self._step_sync(get_raw_document_file(bad_key, storage_service=mock_storage))
        mock_storage.get_file.assert_not_called()

        local_storage = StorageService(backend="local")
        for outside_key in ("pyproject.toml", "../.env"):
            with self.assertRaises(FileNotFoundError):
                self._step_sync(local_storage.get_file(outside_key))

    def test_gemini_overload_fails_over_once_without_triple_retry_storm(self):
        from types import SimpleNamespace
        from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
        from api.services.ai.interfaces.ocr import BaseOCRProvider
        from api.services.ai.managers.ocr_manager import VisionOCRManager
        from api.services.ai.providers.ocr.gemini import GeminiOCRProvider

        cooldown_tracker.clear_all()
        gemini_calls: list[str] = []

        async def _always_503(model: str, contents):
            gemini_calls.append(model)
            raise RuntimeError("503 UNAVAILABLE")

        mock_client = SimpleNamespace(
            aio=SimpleNamespace(models=SimpleNamespace(generate_content=_always_503))
        )
        gemini = GeminiOCRProvider(
            api_key="test-key",
            default_model="gemini-3.5-flash-lite",
            fallback_model="gemini-3.1-flash-lite",
            client=mock_client,
        )

        class FakeGroq(BaseOCRProvider):
            provider_name = "groq"
            default_model = "qwen/qwen3.8-27b"
            is_available = lambda self: True

            async def extract_text(self, image_bytes: bytes, mime_type: str, prompt: str, allow_empty: bool = True) -> str:
                return "Groq fallback ok"

        manager = VisionOCRManager(
            providers=[gemini, FakeGroq()],
            provider_order=["gemini", "groq"],
            max_retries_per_provider=3,
        )
        text = self._step_sync(
            manager.ocr_image_bytes(b"img", mime_type="image/jpeg", raise_on_error=True, allow_empty=False)
        )
        self.assertEqual(text, "Groq fallback ok")
        # Each Gemini candidate model is called at most once (single sweep, not 3 outer retries)
        self.assertEqual(len(gemini_calls), len(set(gemini_calls)))

    def test_reprocess_preserves_qdrant_on_embed_failure_and_logs_uuid_safely(self):
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import UUID
        from api.constants.enums import DocumentSourceType, DocumentStatus
        from api.schemas.document import DocumentUpdate
        from api.services.document import DocumentService

        doc_id = UUID("018e3a2b-7c10-7b56-8a5e-851944621ef0")
        now = datetime.now(timezone.utc)
        mock_doc = MagicMock(
            id=doc_id,
            title="Quy chế đào tạo",
            category_id=None,
            file_name="test.txt",
            file_path="documents/upload/2026/11/test.txt",
            file_size=100,
            file_type="txt",
            file_hash="hash123",
            source_url=None,
            source_type=DocumentSourceType.UPLOAD,
            status=DocumentStatus.INDEXED,
            created_by_id=None,
            total_pages=1,
            chunk_count=1,
            error_message=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
            category=None,
        )

        doc_repo = AsyncMock()
        doc_repo.get_by_id.return_value = mock_doc
        doc_repo.update.return_value = mock_doc
        doc_repo.get_with_category.return_value = mock_doc
        chunk_repo = AsyncMock()
        cat_repo = AsyncMock()
        embedder = AsyncMock()
        embedder.generate_embeddings_batch.side_effect = RuntimeError("Embedding quota exceeded")
        vector_store = AsyncMock()

        service = DocumentService(doc_repo, chunk_repo, cat_repo, embedder, vector_store, storage_service=AsyncMock())
        with patch.object(
            service.parser,
            "parse_async",
            AsyncMock(return_value=[{"page_number": 1, "text": "Điều 1. Nội dung hợp lệ để lập chỉ mục."}]),
        ):
            with self.assertRaises(RuntimeError):
                self._step_sync(service._execute_indexing_pipeline(mock_doc, b"data", "test.txt"))

        chunk_repo.delete_by_document_id.assert_not_awaited()
        vector_store.delete_by_document_id.assert_not_awaited()

        vector_store.update_payload_by_document_id.side_effect = RuntimeError("Qdrant down")
        updated = self._step_sync(service.update_document(doc_id, DocumentUpdate(title="Tiêu đề mới")))
        self.assertEqual(updated.title, "Tiêu đề mới")

        # Soft-delete committed during embedding aborts before writing Qdrant points or DB chunks
        embedder.generate_embeddings_batch.side_effect = None
        embedder.generate_embeddings_batch.return_value = [[0.1, 0.2]]
        doc_repo.is_active.reset_mock()
        doc_repo.is_active.side_effect = [True, False]
        vector_store.upsert_chunks.reset_mock()
        chunk_repo.create_bulk.reset_mock()
        with patch.object(
            service.parser,
            "parse_async",
            AsyncMock(return_value=[{"page_number": 1, "text": "Điều 1. Nội dung hợp lệ để lập chỉ mục."}]),
        ):
            self._step_sync(service._execute_indexing_pipeline(mock_doc, b"data", "test.txt"))
        self.assertEqual(doc_repo.is_active.await_count, 2)
        vector_store.upsert_chunks.assert_not_awaited()
        chunk_repo.create_bulk.assert_not_awaited()


class TestDocumentParserAsyncOCR(unittest.IsolatedAsyncioTestCase):
    """Verify scanned PDF OCR fails loudly and falls back across Vision OCR providers."""

    async def test_extract_pdf_async_raises_when_ocr_fails_on_a_page(self):
        from unittest.mock import AsyncMock, patch
        import pymupdf

        doc = pymupdf.open()
        p1 = doc.new_page()
        p1.insert_text((50, 50), "Trang 1 có văn bản điện tử hợp lệ.")
        doc.new_page()  # Trang 2 là trang scan trống text layer
        pdf_bytes = doc.tobytes()
        doc.close()

        with (
            patch("api.services.rag.parser.ocr_manager.has_available_provider", return_value=True),
            patch("api.services.rag.parser.DocumentParser._render_page_for_ocr", return_value=b"fake-png"),
            patch(
                "api.services.rag.parser.ocr_manager.ocr_images_batch",
                new_callable=AsyncMock,
                return_value=[RuntimeError("429 Rate limit")],
            ),
        ):
            with self.assertRaises(BadRequestException) as ctx:
                await DocumentParser.extract_text_from_pdf_async(pdf_bytes, enable_ocr=True)
            self.assertIn("trang 2", ctx.exception.message.lower())

    async def test_ocr_recitation_fallback_to_openai_vision(self):
        from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
        from api.services.ai.interfaces.ocr import BaseOCRProvider, OCRBlockedError
        from api.services.ai.managers.ocr_manager import VisionOCRManager

        class FakeOCRProvider(BaseOCRProvider):
            def __init__(self, name: str, result: str | Exception):
                self.provider_name = name
                self.default_model = f"mock-{name}"
                self._result = result
                self.calls = 0

            def is_available(self) -> bool:
                return True

            async def extract_text(self, image_bytes: bytes, mime_type: str, prompt: str, allow_empty: bool = True) -> str:
                self.calls += 1
                if isinstance(self._result, Exception):
                    raise self._result
                return self._result

        cooldown_tracker.clear_all()
        gemini = FakeOCRProvider("gemini", OCRBlockedError("FinishReason.RECITATION"))
        groq = FakeOCRProvider("groq", "Điều 12. Công nhận tín chỉ")
        manager = VisionOCRManager(providers=[gemini, groq], provider_order=["gemini", "groq"])

        text = await manager.ocr_image_bytes(
            image_bytes=b"fake-png",
            raise_on_error=True,
            allow_empty=False,
        )
        self.assertEqual(text, "Điều 12. Công nhận tín chỉ")
        self.assertEqual(gemini.calls, 1)  # blocked error fails fast without retry
        self.assertEqual(groq.calls, 1)

    async def test_ocr_404_cools_down_provider(self):
        import httpx
        from api.services.ai.fallback.cooldown_tracker import cooldown_tracker
        from api.services.ai.interfaces.ocr import BaseOCRProvider
        from api.services.ai.managers.ocr_manager import VisionOCRManager

        class Failing404Provider(BaseOCRProvider):
            provider_name = "groq"
            default_model = "bad-model"

            def __init__(self):
                self.calls = 0

            def is_available(self) -> bool:
                return True

            async def extract_text(self, image_bytes: bytes, mime_type: str, prompt: str, allow_empty: bool = True) -> str:
                self.calls += 1
                req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
                resp = httpx.Response(404, request=req, text='{"error":{"message":"model not found"}}')
                raise httpx.HTTPStatusError("404 Not Found", request=req, response=resp)

        class OkProvider(BaseOCRProvider):
            provider_name = "openrouter"
            default_model = "ok-model"

            def is_available(self) -> bool:
                return True

            async def extract_text(self, image_bytes: bytes, mime_type: str, prompt: str, allow_empty: bool = True) -> str:
                return "Nội dung fallback"

        cooldown_tracker.clear_all()
        groq = Failing404Provider()
        openrouter = OkProvider()
        manager = VisionOCRManager(providers=[groq, openrouter], provider_order=["groq", "openrouter"], max_retries_per_provider=3)

        first = await manager.ocr_image_bytes(b"fake-jpg", mime_type="image/jpeg", raise_on_error=True, allow_empty=False)
        second = await manager.ocr_image_bytes(b"fake-jpg", mime_type="image/jpeg", raise_on_error=True, allow_empty=False)
        self.assertEqual(first, "Nội dung fallback")
        self.assertEqual(second, "Nội dung fallback")
        self.assertEqual(groq.calls, 1)  # Cooled down on first 404, never called again

    async def test_gemini_ocr_fallback_model_on_recitation_and_503(self):
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        from api.services.ai.providers.ocr.gemini import GeminiOCRProvider

        called_models: list[str] = []

        async def _fake_generate(model: str, contents):
            called_models.append(model)
            if model == "gemini-primary":
                return SimpleNamespace(
                    text="",
                    candidates=[SimpleNamespace(finish_reason="FinishReason.RECITATION")],
                )
            return SimpleNamespace(text="Điều 1. Phạm vi điều chỉnh", candidates=[])

        mock_client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(side_effect=_fake_generate))))
        provider = GeminiOCRProvider(
            api_key="test-key",
            default_model="gemini-primary",
            fallback_model="gemini-secondary",
            client=mock_client,
        )
        res = await provider.extract_text(b"fake-jpg", "image/jpeg", "OCR", allow_empty=False)
        self.assertEqual(res, "Điều 1. Phạm vi điều chỉnh")
        self.assertEqual(called_models, ["gemini-primary", "gemini-secondary"])


class TestTextChunker(unittest.TestCase):
    """Unit tests for TextChunker text splitting and overlap logic."""

    def test_chunker_empty_pages_produce_no_chunks(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        pages = [
            {"page_number": 1, "text": ""},
            {"page_number": 2, "text": "   \n\n   "},
        ]
        chunks = chunker.chunk_pages(pages)
        self.assertEqual(len(chunks), 0)

    def test_chunker_basic_splitting(self):
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        pages = [
            {
                "page_number": 1,
                "text": "Paragraph 1: Academic rules at HUCE.\n\nParagraph 2: Credit calculation formula.",
            }
        ]
        chunks = chunker.chunk_pages(pages)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 1)
        self.assertIn("content", chunks[0])
        self.assertIn("token_count", chunks[0])

    def test_chunker_extreme_overlap_clamped_no_infinite_loop(self):
        # chunk_overlap >= chunk_size must be safely clamped
        chunker = TextChunker(chunk_size=50, chunk_overlap=100)
        self.assertLess(chunker.chunk_overlap, chunker.chunk_size)

        # Long text without double newlines must advance and terminate
        long_text = "HUCE " * 100
        pages = [{"page_number": 1, "text": long_text}]
        chunks = chunker.chunk_pages(pages)

        self.assertGreater(len(chunks), 1)
        # Verify chunk indices are sequential
        for idx, c in enumerate(chunks):
            self.assertEqual(c["chunk_index"], idx)

    def test_estimate_tokens(self):
        text = "Trường Đại học Xây dựng Hà Nội"
        tokens = TextChunker.estimate_tokens(text)
        self.assertGreater(tokens, 0)


if __name__ == "__main__":
    unittest.main()
