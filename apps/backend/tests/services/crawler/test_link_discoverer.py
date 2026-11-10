import unittest
from bs4 import BeautifulSoup
from api.services.crawler.core.link_discoverer import LinkDiscoverer

HTML_WITH_MEDIA = """
<div class="content">
    <p>Quyết định kèm theo:</p>
    <a href="/files/quyet-dinh.pdf">Tải về Quyết định</a>
    <a href="https://ctsv.huce.edu.vn/docs/phu-luc.PDF">Phụ lục</a>
    <a href="/tin-tuc">Xem tin khác</a>
    <img src="/images/so-do.png" alt="Sơ đồ quy trình" width="600" height="400" />
    <img src="/icons/icon-arrow.svg" alt="icon" width="16" height="16" />
    <img src="data:image/png;base64,iVBORw0KGgoAAA..." alt="tracking" />
</div>
"""


class TestLinkDiscoverer(unittest.TestCase):
    def test_discover_pdfs_and_images(self):
        soup = BeautifulSoup(HTML_WITH_MEDIA, "lxml")
        base_url = "https://ctsv.huce.edu.vn/thong-bao-1"
        discovered = LinkDiscoverer.discover(soup, base_url)

        # Should discover 2 PDFs, resolved to absolute URLs
        pdf_urls = [p.url for p in discovered.pdfs]
        self.assertEqual(len(pdf_urls), 2)
        self.assertIn("https://ctsv.huce.edu.vn/files/quyet-dinh.pdf", pdf_urls)
        self.assertIn("https://ctsv.huce.edu.vn/docs/phu-luc.PDF", pdf_urls)

        # Should discover genuine content image, filtering out icons and base64
        image_urls = [img.url for img in discovered.images]
        self.assertEqual(len(image_urls), 1)
        self.assertIn("https://ctsv.huce.edu.vn/images/so-do.png", image_urls)
