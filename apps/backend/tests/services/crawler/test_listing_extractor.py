import unittest
from api.services.crawler.discovery.listing_extractor import ListingExtractor

SAMPLE_LISTING_HTML = """
<div class="main-content">
    <div class="news-list">
        <article class="post-item">
            <h3 class="post-title"><a href="/thong-bao-hoc-bong-2026">Thông báo học bổng kỳ 2</a></h3>
            <span class="post-date">10/11/2026</span>
            <p class="summary">Xét cấp học bổng cho sinh viên đạt điểm xuất sắc...</p>
        </article>
        <article class="post-item">
            <h3 class="post-title"><a href="/quyet-dinh-khen-thuong">Quyết định khen thưởng</a></h3>
            <span class="post-date">08/11/2026</span>
        </article>
    </div>
    <div class="pagination">
        <a href="/danh-muc?page=2">Trang 2</a>
    </div>
    <div class="footer"><a href="/lien-he">Liên hệ</a></div>
</div>
"""


class TestListingExtractor(unittest.TestCase):
    def test_extract_article_items_from_listing(self):
        items = ListingExtractor.extract_items(
            html=SAMPLE_LISTING_HTML,
            base_url="https://ctsv.huce.edu.vn/danh-muc",
        )
        self.assertEqual(len(items), 2)
        urls = [item.url for item in items]
        self.assertIn("https://ctsv.huce.edu.vn/thong-bao-hoc-bong-2026", urls)
        self.assertIn("https://ctsv.huce.edu.vn/quyet-dinh-khen-thuong", urls)
        self.assertEqual(items[0].published_at, "10/11/2026")
