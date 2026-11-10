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


if __name__ == "__main__":
    unittest.main()
