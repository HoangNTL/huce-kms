import unittest

from api.services.rag.cleaner import TextCleaner


class TestRAGPreviewExtraction(unittest.TestCase):
    """Unit and service tests for RAG extraction preview functionality."""

    def test_extract_and_clean_preview(self):
        file_content = (
            "TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\n"
            "Trang 1/5\n"
            "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng.\n"
            "Quy chế này quy định về đào tạo đại học chính quy."
        ).encode("utf-8")

        preview = TextCleaner.extract_and_clean_preview(
            file_bytes=file_content,
            file_name="quy_che.txt",
        )

        self.assertEqual(preview.file_name, "quy_che.txt")
        self.assertEqual(preview.total_pages, 1)
        self.assertGreater(preview.total_cleaned_chars, 0)
        self.assertLess(preview.total_cleaned_chars, preview.total_raw_chars)

        first_page = preview.pages[0]
        self.assertEqual(first_page.page_number, 1)
        self.assertNotIn("Trang 1/5", first_page.cleaned_text)
        self.assertIn("Trang 1/5", first_page.removed_noise)
        self.assertIn("Điều 1", first_page.cleaned_text)

    def test_chunk_preview_generation(self):
        from api.services.rag.chunker import TextChunker

        text = (
            "CHƯƠNG I: QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi điều chỉnh\n"
            "Nội dung quy định về tuyển sinh và đào tạo.\n\n"
            "Điều 2. Đối tượng tuyển sinh\n"
            "Công dân Việt Nam tốt nghiệp THPT."
        )

        preview = TextChunker.generate_chunk_preview(
            text=text,
            strategy="legal_structural",
            document_title="Quy chế tuyển sinh 2026",
            chunk_size=500,
        )

        self.assertEqual(preview.strategy, "legal_structural")
        self.assertEqual(preview.total_chunks, 2)
        self.assertGreater(preview.avg_tokens, 0)

        c1 = preview.chunks[0]
        self.assertIn("Điều 1", c1.heading_path)
        self.assertIn("[Tài liệu: Quy chế tuyển sinh 2026]", c1.content)

        c2 = preview.chunks[1]
        self.assertIn("Điều 2", c2.heading_path)
        self.assertIn("Công dân Việt Nam", c2.content)

    def test_preview_retrieval_service(self):
        from api.schemas.rag import SearchResultItem
        from api.services.rag.service import RAGService

        sample_chunks = [
            SearchResultItem(
                id="point-1",
                score=0.88,
                document_id=10,
                title="Quy định học vụ",
                page_number=2,
                chunk_index=1,
                content="Sinh viên được đăng ký tối đa 24 tín chỉ mỗi kỳ.",
            )
        ]

        preview = RAGService.assemble_retrieval_preview(
            query="Đăng ký tối đa bao nhiêu tín chỉ?",
            chunks=sample_chunks,
        )

        self.assertEqual(preview.query, "Đăng ký tối đa bao nhiêu tín chỉ?")
        self.assertEqual(preview.total_found, 1)
        self.assertEqual(preview.retrieved_chunks[0].score, 0.88)
        self.assertEqual(preview.retrieved_chunks[0].title, "Quy định học vụ")
        self.assertIn("institutional context", preview.assembled_prompt_preview.lower())
        self.assertIn("24 tín chỉ", preview.assembled_prompt_preview)


if __name__ == "__main__":
    unittest.main()
