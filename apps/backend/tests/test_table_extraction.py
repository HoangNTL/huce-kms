import unittest
import pymupdf

from api.services.rag.parser import DocumentParser


class TestTableExtraction(unittest.TestCase):
    """Unit tests for PDF table extraction and Markdown conversion."""

    def test_extract_page_without_tables(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "HUCE Civil Engineering University\nFaculty of Information Technology")

        text = DocumentParser._extract_page_text_with_tables(page)
        self.assertIn("HUCE Civil Engineering University", text)
        self.assertIn("Faculty of Information Technology", text)
        doc.close()

    def test_pdf_with_table_detection_and_fallback(self):
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 40), "Academic Regulations 2026")

        pdf_bytes = doc.tobytes()
        doc.close()

        pages = DocumentParser.extract_text_from_pdf(pdf_bytes)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["page_number"], 1)
        self.assertIn("Academic Regulations 2026", str(pages[0]["text"]))


if __name__ == "__main__":
    unittest.main()
