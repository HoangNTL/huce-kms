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

        # Check breadcrumbs and structured context/metadata separated from clean content
        chunk1 = chunks[0]
        self.assertEqual(chunk1["page_number"], 1)
        self.assertEqual(chunk1["page_start"], 1)
        self.assertEqual(chunk1["page_end"], 1)
        self.assertIn("Chương I", chunk1["heading_path"])
        self.assertIn("Điều 1", chunk1["heading_path"])
        self.assertIn(document_title, chunk1["context"])
        self.assertNotIn(f"[Tài liệu: {document_title}]", chunk1["content"])
        self.assertEqual(chunk1["metadata"]["article_no"], 1)
        self.assertIn("1", chunk1["metadata"]["clauses"])
        self.assertTrue(chunk1["content_hash"])
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

    def test_markdown_bold_headings_and_page_tracking_and_preamble_no_dup(self):
        pages = [
            {
                "page_number": 1,
                "text": "BỘ GIÁO DỤC VÀ ĐÀO TẠO\nQUYẾT ĐỊNH\n\nĐiều 1. Ban hành kèm theo Quyết định này.",
            },
            {
                "page_number": 4,
                "text": "Điều 3. Phương thức tổ chức đào tạo\n1. Đào tạo theo tín chỉ.\n\n**Điều 4. Hình thức đào tạo**\n1. Đào tạo chính quy.",
            },
            {
                "page_number": 6,
                "text": "**Chương II**\n**LẬP KẾ HOẠCH VÀ TỔ CHỨC GIẢNG DẠY**\n\n**Điều 6. Kế hoạch giảng dạy**\n1. Chi tiết kế hoạch.",
            },
            {
                "page_number": 25,
                "text": "Phụ lục 2\n\nQUY TRÌNH RÚT BỚT HỌC PHẦN\nBước 1: Nộp đơn.",
            },
        ]
        chunker = LegalStructuralChunker(
            document_title="Quy chế đào tạo trình độ đại học",
            max_chunk_size=1200,
        )
        chunks = chunker.chunk_pages(pages)

        # Chunk 0 (preamble) must have clean content and context without duplicated title
        self.assertEqual(chunks[0]["heading_path"], "")
        self.assertEqual(chunks[0]["context"], "Quy chế đào tạo trình độ đại học")
        self.assertNotIn("[Tài liệu:", chunks[0]["content"])

        # Bold **Điều 4** and **Chương II** / **Điều 6** must update headings & pages properly
        headings = [c["heading_path"] for c in chunks]
        self.assertTrue(any("Điều 4: Hình thức đào tạo" in h for h in headings))
        self.assertTrue(any("Chương II: LẬP KẾ HOẠCH VÀ TỔ CHỨC GIẢNG DẠY > Điều 6: Kế hoạch giảng dạy" == h for h in headings))
        self.assertTrue(any("Phụ lục 2: QUY TRÌNH RÚT BỚT HỌC PHẦN" == h for h in headings))

        dieu6 = next(c for c in chunks if "Điều 6" in c["heading_path"])
        self.assertEqual(dieu6["page_number"], 6)
        self.assertEqual(dieu6["page_start"], 6)
        self.assertEqual(dieu6["page_end"], 6)
        self.assertEqual(dieu6["metadata"]["article_no"], 6)
        phuluc2 = next(c for c in chunks if "Phụ lục 2" in c["heading_path"])
        self.assertEqual(phuluc2["page_number"], 25)
        self.assertEqual(phuluc2["metadata"]["appendix_no"], "2")

    def test_lead_in_colon_stays_attached_to_list_items(self):
        pages = [
            {
                "page_number": 4,
                "text": (
                    "Điều 3. Phương thức tổ chức đào tạo\n"
                    "1. Phần giới thiệu dài vừa đủ để lấp đầy phần đầu của chunk thứ nhất trong bài kiểm thử này.\n\n"
                    "b) Các loại học phần:\n\n"
                    "- Học phần bắt buộc là học phần chính yếu.\n\n"
                    "- Học phần tự chọn là học phần mở rộng."
                ),
            }
        ]
        chunker = LegalStructuralChunker(max_chunk_size=220)
        chunks = chunker.chunk_pages(pages)
        self.assertGreaterEqual(len(chunks), 2)
        for c in chunks:
            self.assertFalse(c["content"].rstrip().endswith("b) Các loại học phần:"))

    def test_decision_attachment_and_bilingual_appendices_context_reset(self):
        pages = [
            {
                "page_number": 1,
                "text": (
                    "QUYẾT ĐỊNH\n\n"
                    "Điều 1. Ban hành quy định.\n\n"
                    "Điều 3. Trưởng các đơn vị chịu trách nhiệm thi hành.\n"
                    "Nơi nhận:\n- Lưu VT.\n"
                    "KT. HIỆU TRƯỞNG\nPGS.TS. Bùi Phú Doanh\n"
                    "BỘ PHẨM CHẤT TỐT NGHIỆP\n"
                    "(Kèm theo Quyết định số: 1376/QĐ-ĐHXDHN ngày 28/7/2025)\n"
                    "1. Tên gọi\nTên tiếng Việt."
                ),
            },
            {
                "page_number": 5,
                "text": (
                    "PHỤ LỤC 1\nBộ tiêu chuẩn AUN-QA\n\n"
                    "1. Tiêu chuẩn 1\nNội dung tiêu chuẩn 1."
                ),
            },
            {
                "page_number": 9,
                "text": (
                    "PHỤ LỤC 2\nBảng mô tả Khung trình độ\n\n"
                    "| Bậc | Kết quả |\n| --- | --- |\n| 6 | Cử nhân |"
                ),
            },
            {
                "page_number": 11,
                "text": (
                    "UNIVERSITY GRADUATE ATTRIBUTES\n"
                    "(Issued under Decision No 1376/QĐ-HUCE dated 28 July 2025)\n"
                    "1. Title\nEnglish title."
                ),
            },
            {
                "page_number": 15,
                "text": (
                    "APPENDIX 1\nAUN-QA Criteria\n\n"
                    "1. Criterion 1\nExpected Learning Outcomes."
                ),
            },
        ]
        chunks = LegalStructuralChunker(
            document_title="Bộ phẩm chất tốt nghiệp",
            max_chunk_size=1200,
        ).chunk_pages(pages)

        vi_attached = next(c for c in chunks if "1. Tên gọi" in c["content"])
        self.assertNotIn("Điều 3", vi_attached["context"])
        self.assertIsNone(vi_attached["metadata"].get("article_no"))

        phuluc1 = next(c for c in chunks if "1. Tiêu chuẩn 1" in c["content"])
        self.assertIn("Phụ lục 1: Bộ tiêu chuẩn AUN-QA", phuluc1["context"])
        self.assertIn("Bộ tiêu chuẩn AUN-QA", phuluc1["content"])

        en_attached = next(c for c in chunks if "1. Title" in c["content"])
        self.assertNotIn("Phụ lục 2", en_attached["context"])
        self.assertIsNone(en_attached["metadata"].get("appendix_no"))

        app1 = next(c for c in chunks if "1. Criterion 1" in c["content"])
        self.assertIn("Appendix 1: AUN-QA Criteria", app1["context"])
        self.assertEqual(app1["metadata"]["appendix_no"], "1")

    def test_multipage_table_deduplicates_header_and_tracks_exact_pages(self):
        pages = [
            {
                "page_number": 9,
                "text": (
                    "PHỤ LỤC 2\nKhung trình độ\n\n"
                    "| Bậc | Mô tả | Tín chỉ |\n"
                    "| --- | --- | --- |\n"
                    "| 6 | " + ("Kiến thức đại học. " * 25) + "| 120-180 |"
                ),
            },
            {
                "page_number": 10,
                "text": (
                    "| Bậc | Mô tả | Tín chỉ |\n"
                    "| --- | --- | --- |\n"
                    "| 7 | " + ("Kiến thức thạc sĩ. " * 25) + "| 30-60 |\n\n"
                    "(Issued under Decision No 1376/QĐ-HUCE)"
                ),
            },
        ]
        chunks = LegalStructuralChunker(
            document_title="Test Doc",
            max_chunk_size=600,
        ).chunk_pages(pages)

        row6 = next(c for c in chunks if "| 6 |" in c["content"])
        row7 = next(c for c in chunks if "| 7 |" in c["content"])
        self.assertEqual((row6["page_start"], row6["page_end"]), (9, 9))
        self.assertEqual((row7["page_start"], row7["page_end"]), (10, 10))
        self.assertNotIn("(Issued under Decision", row7["content"])

    def test_preamble_metadata_ceremonial_strip_language_tag_and_multiline_attachment(self):
        pages = [
            {
                "page_number": 1,
                "text": (
                    "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
                    "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n"
                    "Độc lập – Tự do – Hạnh phúc\n"
                    "Số: 1376/QĐ-ĐHXDHN\n"
                    "Hà Nội, ngày 28 tháng 7 năm 2025\n"
                    "QUYẾT ĐỊNH\n\n"
                    "Điều 1. Ban hành chuẩn đầu ra.\n\n"
                    "Điều 3. Thi hành Quyết định này.\n"
                    "PGS.TS. Bùi Phú Doanh\n"
                    "BỘ PHẨM CHẤT TỐT NGHIỆP"
                ),
            },
            {
                "page_number": 2,
                "text": (
                    "CỦA TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\n"
                    "(Kèm theo Quyết định số: 1376/QĐ-ĐHXDHN ngày 28/7/2025)\n"
                    "1. Tên gọi\nTiếng Việt."
                ),
            },
            {
                "page_number": 9,
                "text": (
                    "PHỤ LỤC 2\nBảng mô tả Khung trình độ\n\n"
                    "| Bậc | Mô tả |\n| --- | --- |\n| 6 | Cử nhân |"
                ),
            },
            {
                "page_number": 10,
                "text": (
                    "| 7 | Kỹ sư |\n| --- | --- |\n\n"
                    "UNIVERSITY GRADUATE ATTRIBUTES AND LEARNING\n\n"
                    "OUTCOMES OF HANOI UNIVERSITY OF CIVIL ENGINEERING.\n"
                    "(Issued under Decision No 1376/QĐ-HUCE dated 28 July 2025)\n"
                    "1. Title\nEnglish version."
                ),
            },
        ]
        chunks = LegalStructuralChunker(
            document_title="Chuẩn đầu ra HUCE",
            max_chunk_size=1200,
        ).chunk_pages(pages)

        preamble = chunks[0]
        self.assertNotIn("CỘNG HÒA XÃ HỘI", preamble["content"])
        self.assertNotIn("Độc lập – Tự do", preamble["content"])
        self.assertEqual(preamble["metadata"]["chunk_type"], "preamble")
        self.assertEqual(preamble["metadata"]["doc_number"], "1376/QĐ-ĐHXDHN")
        self.assertEqual(preamble["metadata"]["issued_date"], "28/07/2025")
        self.assertEqual(preamble["metadata"]["language"], "vi")

        vi_attached = next(c for c in chunks if "1. Tên gọi" in c["content"])
        self.assertIn("BỘ PHẨM CHẤT TỐT NGHIỆP", vi_attached["content"])
        self.assertIn("CỦA TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI", vi_attached["content"])
        self.assertEqual(vi_attached["metadata"]["language"], "vi")

        phuluc2 = next(c for c in chunks if "| 6 | Cử nhân |" in c["content"])
        self.assertIn("| 7 | Kỹ sư |", phuluc2["content"])
        self.assertNotIn("UNIVERSITY GRADUATE ATTRIBUTES", phuluc2["content"])

        en_attached = next(c for c in chunks if "1. Title" in c["content"])
        self.assertIn("UNIVERSITY GRADUATE ATTRIBUTES", en_attached["content"])
        self.assertIn("OUTCOMES OF HANOI UNIVERSITY", en_attached["content"])
        self.assertEqual(en_attached["metadata"]["language"], "en")

    def test_english_chunk_quoting_vietnamese_title_stays_en(self):
        from api.services.rag.patterns import detect_language

        text = (
            "UNIVERSITY GRADUATE ATTRIBUTES AND LEARNING OUTCOMES\n"
            "1. Title\n"
            "- Vietnamese Title: Bộ Phẩm chất tốt nghiệp và Chuẩn đầu ra cấp cơ sở giáo dục.\n"
            "- English Title: University Graduate Attributes and University Learning Outcomes.\n"
            "2. Objectives\n"
            "The University Graduate Attributes and University Learning Outcomes are established to "
            "operationalize the university vision, mission, and core values in training human resources."
        )
        self.assertEqual(detect_language(text), "en")

    def test_rag_service_search_prefers_matching_query_language(self):
        from uuid import UUID
        from api.schemas.rag import SearchResultItem
        from api.services.rag.patterns import detect_language
        from api.services.rag.service import RAGService

        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        items = [
            SearchResultItem(id="1", document_id=doc_id, title="Doc", page_number=11, chunk_index=0, score=0.91, metadata={"language": "en"}, content="English ULO1"),
            SearchResultItem(id="2", document_id=doc_id, title="Doc", page_number=2, chunk_index=1, score=0.89, metadata={"language": "vi"}, content="Chuẩn đầu ra ULO1"),
            SearchResultItem(id="3", document_id=doc_id, title="Doc", page_number=1, chunk_index=2, score=0.85, metadata={}, content="Legacy untagged chunk"),
        ]
        query_lang = detect_language("Chuẩn đầu ra ULO1 là gì?")
        self.assertEqual(query_lang, "vi")
        results = RAGService._prioritize_by_language(items, query_lang, top_k=2)
        self.assertEqual([r.id for r in results], ["2", "3"])

    def test_wrapped_headings_multipage_subheaders_doc_number_and_attached_form(self):
        pages = [
            {
                "page_number": 1,
                "text": (
                    "BỘ GIÁO DỤC VÀ ĐÀO TẠO\n"
                    "QUY CHẾ\n"
                    "(Ban hành kèm theo quyết định số 300 /QĐ-ĐHXD ngày 27 tháng 6 năm 2017)\n\n"
                    "Điều 5. Đánh giá về ý thức chấp hành nội quy, quy chế, quy định trong\n"
                    "nhà trường\n"
                    "1. Tiêu chí đánh giá.\n\n"
                    "Chương III: PHÂN LOẠI ĐÁNH GIÁ VÀ QUY TRÌNH ĐÁNH GIÁ\n"
                    "\n"
                    "KẾT QUẢ RÈN LUYỆN\n\n"
                    "Điều 9. Phân loại kết quả rèn luyện\n"
                    "1. Các mức xếp loại."
                ),
            },
            {
                "page_number": 6,
                "text": (
                    "Điều 16. Tổ chức thực hiện\n"
                    "1. Quy chế áp dụng từ năm học 2017-2018.\n"
                    "KT. HIỆU TRƯỞNG\n"
                    "PGS.TS Phạm Xuân Anh\n"
                    "PHIẾU ĐÁNH GIÁ KẾT QUẢ RÈN LUYỆN SINH VIÊN\n"
                    "| TT | NỘI DUNG | ĐÁNH GIÁ | |\n"
                    "| --- | --- | --- | --- |\n"
                    "| | | SV | LỚP |\n"
                    "| I | " + ("Ý thức học tập chi tiết. " * 25) + " | | |"
                ),
            },
            {
                "page_number": 7,
                "text": (
                    "| TT | NỘI DUNG | ĐÁNH GIÁ | |\n"
                    "| --- | --- | --- | --- |\n"
                    "| | | SV | LỚP |\n"
                    "| II | Chấp hành nội quy nhà trường. | | |"
                ),
            },
        ]
        chunks = LegalStructuralChunker(
            document_title="Quy chế rèn luyện",
            max_chunk_size=700,
        ).chunk_pages(pages)

        self.assertEqual(chunks[0]["metadata"].get("doc_number"), "300/QĐ-ĐHXD")

        dieu5 = next(c for c in chunks if "Điều 5" in c["heading_path"])
        self.assertIn("quy định trong nhà trường", dieu5["metadata"]["article_title"])

        # Chapter III wrapped title must not spawn an orphan 5-token chunk
        self.assertFalse(any(c["content"].strip() == "KẾT QUẢ RÈN LUYỆN" for c in chunks))
        dieu9 = next(c for c in chunks if "Điều 9" in c["heading_path"])
        self.assertIn("PHÂN LOẠI ĐÁNH GIÁ VÀ QUY TRÌNH ĐÁNH GIÁ KẾT QUẢ RÈN LUYỆN", dieu9["context"])

        # Attached evaluation form after signature resets article_no and drops repeated sub-header
        form_chunks = [c for c in chunks if "PHIẾU ĐÁNH GIÁ KẾT QUẢ RÈN LUYỆN SINH VIÊN" in c["context"]]
        self.assertGreaterEqual(len(form_chunks), 1)
        for fc in form_chunks:
            self.assertIsNone(fc["metadata"].get("article_no"))
            self.assertFalse(fc["content"].rstrip().endswith("| | | SV | LỚP |"))


if __name__ == "__main__":
    unittest.main()
