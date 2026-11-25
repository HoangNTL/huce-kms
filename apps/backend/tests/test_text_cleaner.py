import unittest
from api.services.rag.cleaner import TextCleaner


class TestTextCleaner(unittest.TestCase):
    """Unit tests for TextCleaner module."""

    def test_unicode_nfc_normalization(self):
        import unicodedata
        # Canonical NFD (decomposed) string for Vietnamese
        expected = "Trường Đại học Xây dựng Hà Nội"
        nfd_str = unicodedata.normalize("NFD", expected)
        cleaned = TextCleaner.normalize_unicode(nfd_str)
        self.assertEqual(cleaned, expected)

    def test_remove_headers_and_footers(self):
        raw = (
            "TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\n"
            "PHÒNG ĐÀO TẠO\n"
            "Quy chế đào tạo đại học năm 2026\n"
            "Trang 1/10"
        )
        cleaned, noise = TextCleaner.clean_page_text(raw)
        self.assertNotIn("Trang 1/10", cleaned)
        self.assertIn("Trang 1/10", noise)

    def test_remove_bare_page_numbers_header_footer(self):
        raw = (
            "14\n"
            "Chương VI\n"
            "ĐIỀU KHOẢN THI HÀNH\n"
            "Điều 34. Hiệu lực thi hành\n"
        )
        cleaned, noise = TextCleaner.clean_page_text(raw)
        self.assertIn("14", noise)
        self.assertFalse(cleaned.startswith("14"))
        self.assertTrue(cleaned.startswith("Chương VI"))

    def test_dehyphenation_and_spacing(self):
        raw = "quy định về đăng ký học\nphần của sinh    viên."
        cleaned, _ = TextCleaner.clean_page_text(raw)
        self.assertIn("học phần", cleaned)
        self.assertNotIn("    ", cleaned)

    def test_clean_pages_pipeline(self):
        pages = [
            {"page_number": 1, "text": "Trang 1/2\nNội dung trang 1."},
            {"page_number": 2, "text": "Trang 2/2\nNội dung trang 2."},
        ]
        cleaned_pages = TextCleaner.clean_pages(pages)
        self.assertEqual(len(cleaned_pages), 2)
        self.assertEqual(cleaned_pages[0]["page_number"], 1)
        self.assertIn("cleaned_text", cleaned_pages[0])
        self.assertNotIn("Trang 1/2", cleaned_pages[0]["cleaned_text"])
        self.assertIn("Trang 1/2", cleaned_pages[0]["removed_noise"])

    def test_does_not_merge_numbered_heading_with_lettered_subitem(self):
        raw = (
            "3. Giải thích từ ngữ\n"
            "a) Phẩm chất tốt nghiệp cơ sở giáo dục đại học.\n"
            "3. Definitions\n"
            "a) University Graduate Attributes."
        )
        cleaned, _ = TextCleaner.clean_page_text(raw)
        self.assertIn("3. Giải thích từ ngữ\na) Phẩm chất", cleaned)
        self.assertIn("3. Definitions\na) University", cleaned)

    def test_merges_dangling_connectors_and_preserves_hyphens_and_repairs_syllables(self):
        raw = (
            "Thông tư của Bộ Giáo dục và\nĐào tạo ban hành quy định.\n"
            "Established in\n1998, among\nASEAN member countries.\n"
            "Khối lượng 120-\n180 tín chỉ theo chuẩn AUN-\nQA.\n"
            "Phẩ m chấ t tố t và lý th uyế t ch uyên ngành , , , truyề n đ ạt."
        )
        cleaned, _ = TextCleaner.clean_page_text(raw)
        self.assertIn("Bộ Giáo dục và Đào tạo", cleaned)
        self.assertIn("Established in 1998, among ASEAN", cleaned)
        self.assertIn("120-180", cleaned)
        self.assertIn("AUN-QA", cleaned)
        self.assertIn("Phẩm chất tốt", cleaned)
        self.assertIn("thuyết chuyên", cleaned)
        self.assertIn("truyền đạt.", cleaned)
        self.assertNotIn(", , ,", cleaned)

    def test_strip_repeated_cross_page_headers_and_footers(self):
        pages = [
            {"page_number": 1, "text": "TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\nNội dung trang một.\nTài liệu nội bộ - 1"},
            {"page_number": 2, "text": "TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\nNội dung trang hai.\nTài liệu nội bộ - 2"},
            {"page_number": 3, "text": "TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI\nNội dung trang ba.\nTài liệu nội bộ - 3"},
        ]
        cleaned_pages = TextCleaner.clean_pages(pages)
        for p in cleaned_pages:
            self.assertNotIn("TRƯỜNG ĐẠI HỌC XÂY DỰNG HÀ NỘI", p["cleaned_text"])
            self.assertNotIn("Tài liệu nội bộ", p["cleaned_text"])
            self.assertIn("Nội dung trang", p["cleaned_text"])

    def test_clean_form_blanks_and_doc_slash_keeps_single_ellipsis(self):
        raw = (
            "Ban hành kèm theo quyết định số 300 /QĐ-ĐHXD.\n"
            "a) Ý thức chấp hành nội quy, giảng viên,…\n"
            "Họ tên:………………………………………….…… Mã số SV:………….…………. Lớp:………………\n"
            "…………………………………………………………………………………………….\n"
            "Tổng điểm đánh giá: ……. Xếp loại: ……………\n"
            "Hà Nội, ngày……/…… /20……"
        )
        cleaned, _ = TextCleaner.clean_page_text(raw)
        self.assertIn("300/QĐ-ĐHXD", cleaned)
        self.assertIn("giảng viên,…", cleaned)
        self.assertNotIn("……", cleaned)
        self.assertNotIn("………", cleaned)
        self.assertIn("Họ tên:... Mã số SV:... Lớp:...", cleaned)
        self.assertIn("Tổng điểm đánh giá: ... Xếp loại: ...", cleaned)
        self.assertNotIn("\n...\n", cleaned)

    def test_normalizes_pua_symbol_bullets_and_joins_standalone_bullet_lines(self):
        raw = (
            "Ghi chú:\n\n"
            "\uf02b\n"
            "SV tự đánh giá, nộp cho Lớp trưởng.\n\n"
            "\uf02d\n\n"
            "Chủ tịch Hội đồng: Hiệu trưởng.\n"
            "\uf02b Từ 90-100 điểm: Xuất sắc\ue123"
        )
        cleaned, _ = TextCleaner.clean_page_text(raw)
        self.assertNotIn("\uf02b", cleaned)
        self.assertNotIn("\uf02d", cleaned)
        self.assertNotIn("\ue123", cleaned)
        self.assertIn("- SV tự đánh giá, nộp cho Lớp trưởng.", cleaned)
        self.assertIn("- Chủ tịch Hội đồng: Hiệu trưởng.", cleaned)
        self.assertIn("- Từ 90-100 điểm: Xuất sắc", cleaned)


if __name__ == "__main__":
    unittest.main()
