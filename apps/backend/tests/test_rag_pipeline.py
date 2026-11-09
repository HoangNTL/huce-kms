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


class TestTextChunker(unittest.TestCase):
    """Unit tests for TextChunker text splitting and overlap logic."""

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
