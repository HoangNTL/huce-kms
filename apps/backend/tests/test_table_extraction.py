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

    def test_bordered_table_no_col_placeholders_no_external_header_and_clean_vi(self):
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        # Title directly above table (must NOT be swallowed as external table header)
        page.insert_text((50, 75), "APPENDIX 2")
        page.insert_text((50, 92), "Vietnam Qualifications Framework (VQF)")

        # Draw a 3x3 bordered table (top row has merged cols 2-3)
        x_cols = [50, 150, 350, 540]
        y_rows = [105, 135, 165, 220]
        for y in y_rows:
            page.draw_line((x_cols[0], y), (x_cols[-1], y), color=(0, 0, 0))
        page.draw_line((x_cols[0], y_rows[0]), (x_cols[0], y_rows[-1]), color=(0, 0, 0))
        page.draw_line((x_cols[1], y_rows[0]), (x_cols[1], y_rows[-1]), color=(0, 0, 0))
        page.draw_line((x_cols[2], y_rows[1]), (x_cols[2], y_rows[-1]), color=(0, 0, 0))  # merged in row 0
        page.draw_line((x_cols[3], y_rows[0]), (x_cols[3], y_rows[-1]), color=(0, 0, 0))

        page.insert_text((60, 125), "Level")
        page.insert_text((210, 125), "Learning Outcomes")
        page.insert_text((60, 155), "6")
        page.insert_text((160, 155), "Group 1: Knowledge")
        page.insert_text((360, 155), "Group 2: Skills")
        page.insert_text((60, 185), "Bachelor")
        page.insert_text((160, 185), "- Solid practical")
        page.insert_text((160, 200), "knowledge")
        page.insert_text((360, 185), "- Complex problem")
        page.insert_text((360, 200), "solving")

        text = DocumentParser._extract_page_text_with_tables(page)
        doc.close()

        self.assertIn("Vietnam Qualifications Framework (VQF)", text)
        self.assertNotIn("Col3", text)
        self.assertNotIn("|APPENDIX 2", text)
        self.assertNotIn("|Group 2: Skills|Group 2: Skills|", text)
        self.assertIn("- Solid practical knowledge", text)
        self.assertIn("- Complex problem solving", text)

    def test_garbled_page_detection(self):
        garbled_en = (
            "| 7 | Prof ound , b road and ad vanced th eoreti cal and practi cal k nowl ed ge; "
            "b d h di d i d f i l i Anal yti cal , synth esi s , and eval uati ve skill s |"
        )
        garbled_vi = (
            "Kiế n thức thực tế và lý th uyế t sâu rộng , , , "
            "h ọc th uyế t cơ bản ch uyên ngành truyề n đ ạt thảo l uận"
        )
        clean_vi = (
            "Điều 1. Ban hành Bộ phẩm chất tốt nghiệp và chuẩn đầu ra cấp cơ sở giáo dục "
            "của Trường Đại học Xây dựng Hà Nội."
        )
        self.assertTrue(DocumentParser._is_garbled_page_text(garbled_en))
        self.assertTrue(DocumentParser._is_garbled_page_text(garbled_vi))
        self.assertFalse(DocumentParser._is_garbled_page_text(clean_vi))

    def test_single_row_bordered_table_preserved_and_sparse_borderless_rejected(self):
        doc = pymupdf.open()
        p1 = doc.new_page(width=595, height=842)
        p1.draw_rect((50, 100, 540, 145), color=(0, 0, 0), width=1)
        p1.draw_line((120, 100), (120, 145), color=(0, 0, 0))
        p1.insert_text((65, 125), "7")
        p1.insert_text((135, 125), "Master Level Outcomes")
        t1 = DocumentParser._extract_page_text_with_tables(p1)

        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((50, 100), "- English Title: University Graduate Attributes (UGAs)")
        p2.insert_text((60, 118), "and University Learning Outcomes (ULOs).")
        t2 = DocumentParser._extract_page_text_with_tables(p2)
        doc.close()

        self.assertIn("| 7 | Master Level Outcomes |", t1)
        self.assertNotIn("|", t2)
        self.assertIn("English Title:", t2)

    def test_merged_cells_no_duplication_and_no_br_and_clean_dots(self):
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        # Draw bordered 3-column rubric table with a tall merged col 0 and missing horizontal borders for 2.2
        xs = [45, 95, 420, 540]
        ys = [60, 90, 140, 175, 210]
        for y in ys:
            if y in (60, 90, 210):
                page.draw_line((xs[0], y), (xs[-1], y), color=(0, 0, 0))
            else:
                page.draw_line((xs[1], y), (xs[-1], y), color=(0, 0, 0))
        for x in xs:
            page.draw_line((x, ys[0]), (x, ys[-1]), color=(0, 0, 0))

        page.insert_text((55, 80), "TT")
        page.insert_text((110, 80), "NOI DUNG DANH GIA")
        page.insert_text((430, 80), "THANG DIEM")
        page.insert_text((55, 118), "2.1")
        page.insert_text((110, 112), "+ Chap hanh tot")
        page.insert_text((110, 128), "+ Da tham gia: ...............")
        page.insert_text((430, 118), "+5 diem")
        page.insert_text((110, 160), "+ Dong cham hoc phi")
        page.insert_text((430, 160), "-3 diem")
        page.insert_text((110, 195), "+ Vi pham")
        page.insert_text((430, 195), "-2 diem")

        text = DocumentParser._extract_page_text_with_tables(page)
        doc.close()

        self.assertNotIn("<br>", text)
        self.assertNotIn("...............", text)
        self.assertEqual(text.count("+ Dong cham hoc phi"), 1)
        self.assertEqual(text.count("+ Vi pham"), 1)
        self.assertIn("+ Da tham gia: ...", text)


if __name__ == "__main__":
    unittest.main()
