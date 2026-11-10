import unittest
from api.services.crawler.core.html_cleaner import HtmlCleaner
from api.services.crawler.core.extractor import HtmlExtractor

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Quy chế tuyển sinh 2026 - HUCE</title>
    <meta property="article:published_time" content="2026-03-15T08:00:00Z" />
</head>
<body>
    <header><nav><a href="/">Trang chủ</a><a href="/tin-tuc">Tin tức</a></nav></header>
    <aside class="sidebar"><div class="widget">Banner quảng cáo tuyển sinh</div></aside>
    <main id="main-content" class="entry-content">
        <h1>Quy chế tuyển sinh 2026</h1>
        <p>Chi tiết về kế hoạch và điều kiện xét tuyển đại học chính quy năm 2026.</p>
        <div class="attachments">
            <a href="/uploads/quy-che-2026.pdf">Tải file PDF Quy chế</a>
        </div>
    </main>
    <footer><p>Bản quyền thuộc ĐH Xây Dựng Hà Nội</p></footer>
    <script>console.log("analytics");</script>
</body>
</html>
"""


class TestHtmlCleaningAndExtraction(unittest.TestCase):
    def test_extract_metadata(self):
        meta = HtmlExtractor.extract_metadata(SAMPLE_HTML, "https://tuyensinh.huce.edu.vn/post-1")
        self.assertIn("Quy chế tuyển sinh 2026", meta.title)
        self.assertEqual(meta.published_at, "2026-03-15T08:00:00Z")

    def test_clean_removes_nav_sidebar_footer(self):
        cleaned = HtmlCleaner.clean_and_isolate_content(SAMPLE_HTML, "https://tuyensinh.huce.edu.vn/post-1")
        self.assertNotIn("Banner quảng cáo", cleaned.main_content_html)
        self.assertNotIn("Bản quyền thuộc", cleaned.main_content_html)
        self.assertNotIn("analytics", cleaned.main_content_html)
        self.assertIn("Chi tiết về kế hoạch và điều kiện xét tuyển", cleaned.main_content_html)
        self.assertIsNotNone(cleaned.soup)
