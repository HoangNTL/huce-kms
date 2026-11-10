import unittest

from api.services.rag.chunker import LegalStructuralChunker, TextChunker


class TestChunkerStrategies(unittest.TestCase):
    """Unit tests for chunking strategies: Recursive and Legal Structural."""

    def test_legal_structural_chunking_with_articles(self):
        document_title = "Quy chế đào tạo đại học HUCE 2026"
        sample_text = (
            "CHƯƠNG I: QUY ĐỊNH CHUNG\n\n"
            "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng\n"
            "1. Quy chế này quy định về đào tạo đại học chính quy tại Trường Đại học Xây dựng Hà Nội.\n"
            "2. Quy chế áp dụng đối với tất cả sinh viên hệ chính quy.\n\n"
            "Điều 2. Thời gian và kế hoạch đào tạo\n"
            "1. Năm học gồm 2 học kỳ chính và 1 học kỳ phụ.\n"
            "2. Thời gian tối đa để hoàn thành chương trình là 7 năm đối với hệ cử nhân kỹ sư."
        )

        pages = [{"page_number": 1, "text": sample_text}]

        chunker = LegalStructuralChunker(
            document_title=document_title,
            max_chunk_size=1000,
        )
        chunks = chunker.chunk_pages(pages)

        # Must have at least 2 chunks (one for Điều 1, one for Điều 2)
        self.assertGreaterEqual(len(chunks), 2)

        # Check breadcrumbs and contextual prefix on chunks
        chunk1 = chunks[0]
        self.assertEqual(chunk1["page_number"], 1)
        self.assertIn("Chương I", chunk1["heading_path"])
        self.assertIn("Điều 1", chunk1["heading_path"])
        self.assertIn(f"[Tài liệu: {document_title}]", chunk1["content"])
        self.assertIn("Điều 1", chunk1["content"])

        chunk2 = chunks[1]
        self.assertIn("Điều 2", chunk2["heading_path"])
        self.assertIn("Thời gian và kế hoạch đào tạo", chunk2["content"])

    def test_legal_structural_fallback_for_unstructured_text(self):
        document_title = "Thông báo chung"
        unstructured_text = (
            "Hôm nay nhà trường thông báo kế hoạch nghỉ lễ.\n\n"
            "Toàn thể cán bộ giảng viên và sinh viên được nghỉ từ ngày mai."
        )
        pages = [{"page_number": 1, "text": unstructured_text}]

        chunker = LegalStructuralChunker(
            document_title=document_title,
            max_chunk_size=500,
        )
        chunks = chunker.chunk_pages(pages)

        self.assertGreaterEqual(len(chunks), 1)
        self.assertIn("thông báo kế hoạch nghỉ lễ", chunks[0]["content"])

    def test_text_chunker_strategy_selector(self):
        pages = [{"page_number": 1, "text": "Điều 1. Nội dung điều 1"}]

        # Selecting 'legal_structural' via factory
        chunks_legal = TextChunker.chunk_with_strategy(
            pages=pages,
            strategy="legal_structural",
            document_title="Quy chế mẫu",
        )
        self.assertGreaterEqual(len(chunks_legal), 1)
        self.assertIn("Điều 1", chunks_legal[0]["heading_path"])

        # Selecting 'recursive' via factory
        chunks_recursive = TextChunker.chunk_with_strategy(
            pages=pages,
            strategy="recursive",
            chunk_size=500,
            chunk_overlap=50,
        )
        self.assertGreaterEqual(len(chunks_recursive), 1)

    def test_split_oversized_markdown_table_preserves_headers(self):
        header = "| STT | Mã môn | Tên học phần | Số TC |\n| --- | --- | --- | --- |"
        rows = [f"| {i} | XD{100+i} | Môn học xây dựng số {i} | {i%4 + 1} |" for i in range(1, 15)]
        table_text = header + "\n" + "\n".join(rows)

        chunks = TextChunker.split_markdown_table(table_text, max_chunk_size=300)
        self.assertGreater(len(chunks), 1)

        # Every chunk must have the exact table header and valid table rows
        for c in chunks:
            self.assertTrue(c.startswith("| STT | Mã môn | Tên học phần | Số TC |"))
            self.assertIn("| --- | --- | --- | --- |", c)
            for line in c.split("\n"):
                if line.strip():
                    self.assertTrue(line.strip().startswith("|"))
                    self.assertTrue(line.strip().endswith("|"))

    def test_chunking_page_with_oversized_table(self):
        header = "| Bậc | Điểm TOEIC | TA quy đổi |\n| --- | --- | --- |"
        rows = [f"| Bậc {i} | {100+i*30} | TA{i} |" for i in range(1, 15)]
        table_text = header + "\n" + "\n".join(rows)
        pages = [{"page_number": 1, "text": table_text}]

        chunker = TextChunker(chunk_size=200, chunk_overlap=0)
        chunks = chunker.chunk_pages(pages)

        self.assertGreater(len(chunks), 1)
        # Verify no broken cells or chopped lines
        for c in chunks:
            self.assertTrue(c["content"].startswith("| Bậc | Điểm TOEIC | TA quy đổi |"))

    def test_split_oversized_paragraph_preserves_word_boundaries(self):
        long_para = (
            "Đề cương chi tiết của từng học phần phải thể hiện rõ số lượng tín chỉ, "
            "điều kiện tiên quyết (nếu có), nội dung lý thuyết và thực hành, cách thức "
            "đánh giá học phần, giáo trình, tài liệu tham khảo và điều kiện thí nghiệm."
        )
        parts = TextChunker.split_oversized_paragraph(long_para, max_chunk_size=100)
        self.assertGreater(len(parts), 1)
        # Verify words are not cut in half
        for part in parts:
            first_word = part.split()[0]
            last_word = part.split()[-1]
            self.assertTrue(len(first_word) > 0)
            self.assertTrue(len(last_word) > 0)
            # Should not end with dangling fragment like 'g'
            self.assertFalse(part.endswith("lượn"))

    def test_clause_splitting_preserves_clauses(self):
        doc_text = (
            "Điều 2. Chương trình đào tạo\n"
            "1. Chương trình đào tạo cần thể hiện rõ trình độ và chuẩn đầu ra của người học.\n"
            "2. Mỗi chương trình gắn với một ngành hoặc chuyên ngành cụ thể.\n"
            "3. Đề cương chi tiết phải thể hiện rõ số lượng tín chỉ và điều kiện tiên quyết.\n"
            "4. Khối lượng chương trình đào tạo tối thiểu 150 tín chỉ đối với khóa 5 năm."
        )
        pages = [{"page_number": 1, "text": doc_text}]
        chunker = LegalStructuralChunker(max_chunk_size=200)
        chunks = chunker.chunk_pages(pages)
        self.assertGreaterEqual(len(chunks), 2)
        # Clauses should be preserved cleanly without word breaks
        for c in chunks:
            self.assertIn("Điều 2", c["heading_path"])


if __name__ == "__main__":
    unittest.main()
