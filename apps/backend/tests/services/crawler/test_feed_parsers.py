import unittest
from api.services.crawler.discovery.sitemap_parser import SitemapParser
from api.services.crawler.discovery.rss_parser import RssParser

SAMPLE_SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://daotao.huce.edu.vn/tin-tuc-1</loc>
        <lastmod>2026-11-09</lastmod>
    </url>
    <url>
        <loc>https://daotao.huce.edu.vn/tin-tuc-2</loc>
    </url>
</urlset>
"""

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Tin tức HUCE</title>
        <item>
            <title>Kế hoạch xét tốt nghiệp</title>
            <link>https://daotao.huce.edu.vn/tot-nghiep-2026</link>
            <pubDate>Mon, 10 Nov 2026 08:00:00 GMT</pubDate>
            <description>Thông tin chi tiết về lễ xét tốt nghiệp đợt 2...</description>
        </item>
    </channel>
</rss>
"""


class TestFeedParsers(unittest.TestCase):
    def test_parse_sitemap(self):
        items = SitemapParser.parse(SAMPLE_SITEMAP, base_url="https://daotao.huce.edu.vn")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].url, "https://daotao.huce.edu.vn/tin-tuc-1")
        self.assertEqual(items[0].published_at, "2026-11-09")

    def test_parse_rss(self):
        items = RssParser.parse(SAMPLE_RSS, base_url="https://daotao.huce.edu.vn")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://daotao.huce.edu.vn/tot-nghiep-2026")
        self.assertEqual(items[0].title, "Kế hoạch xét tốt nghiệp")
        self.assertIn("lễ xét tốt nghiệp", items[0].summary or "")
