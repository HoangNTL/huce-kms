import unittest
from api.services.crawler.core.markdown_converter import MarkdownConverter


class TestMarkdownConverter(unittest.TestCase):
    def test_convert_html_to_markdown_with_table_and_local_links(self):
        html = """
        <h2>Kế hoạch đào tạo</h2>
        <table>
            <tr><th>Học phần</th><th>Số tín chỉ</th></tr>
            <tr><td>Toán cao cấp</td><td>3</td></tr>
        </table>
        <p><a href="https://ctsv.huce.edu.vn/quyet-dinh.pdf">Xem văn bản gốc</a></p>
        <img src="https://ctsv.huce.edu.vn/so-do.png" alt="Sơ đồ" />
        """
        media_mapping = {
            "https://ctsv.huce.edu.vn/quyet-dinh.pdf": "./pdfs/quyet-dinh.pdf",
            "https://ctsv.huce.edu.vn/so-do.png": "./images/so-do.png",
        }
        md = MarkdownConverter.convert(
            html=html,
            title="Kế hoạch đào tạo 2026",
            source_url="https://ctsv.huce.edu.vn/ke-hoach",
            crawled_at="2026-11-10T10:00:00Z",
            media_mapping=media_mapping,
        )
        self.assertIn("# Kế hoạch đào tạo 2026", md)
        self.assertIn("| Học phần | Số tín chỉ |", md)
        self.assertIn("[Xem văn bản gốc](./pdfs/quyet-dinh.pdf)", md)
        self.assertIn("![Sơ đồ](./images/so-do.png)", md)
