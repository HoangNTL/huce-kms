import unittest
from api.services.crawler.discovery.url_normalizer import UrlNormalizer
from api.services.crawler.discovery.schemas import DiscoveredItem, DiscoveryResult


class TestUrlNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = UrlNormalizer(allowed_domains=["huce.edu.vn"])

    def test_normalize_valid_relative_url(self):
        res = self.normalizer.normalize("/quy-che-1", base_url="https://ctsv.huce.edu.vn/danh-muc")
        self.assertEqual(res, "https://ctsv.huce.edu.vn/quy-che-1")

    def test_strips_tracking_params_and_fragments(self):
        url = "https://ctsv.huce.edu.vn/thong-bao?utm_source=fb&utm_medium=cpc#section-2"
        res = self.normalizer.normalize(url)
        self.assertEqual(res, "https://ctsv.huce.edu.vn/thong-bao")

    def test_blocks_external_domain(self):
        res = self.normalizer.normalize("https://google.com/search")
        self.assertIsNone(res)

    def test_discovered_item_schema(self):
        item = DiscoveredItem(
            url="https://ctsv.huce.edu.vn/thong-bao-1",
            title="Thông báo học phần",
            published_at="2026-11-10",
        )
        self.assertEqual(item.status, "discovered")
        self.assertEqual(item.title, "Thông báo học phần")

    def test_discovery_result_schema(self):
        res = DiscoveryResult(
            source_url="https://ctsv.huce.edu.vn/danh-muc",
            total_discovered=1,
            items=[
                DiscoveredItem(
                    url="https://ctsv.huce.edu.vn/thong-bao-1",
                    title="Thông báo 1",
                )
            ],
            discovered_at="2026-11-10T12:00:00Z",
        )
        self.assertEqual(res.total_discovered, 1)
        self.assertEqual(len(res.items), 1)
