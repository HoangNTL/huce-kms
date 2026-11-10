import unittest
from tools.crawler.cli import build_parser


class TestCrawlerCLI(unittest.TestCase):
    def test_parser_crawl_command(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "--url", "https://ctsv.huce.edu.vn/thong-bao-1", "--skip-media"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.url, "https://ctsv.huce.edu.vn/thong-bao-1")
        self.assertTrue(args.skip_media)

    def test_parser_default_options(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "--url", "https://daotao.huce.edu.vn/thong-bao-2"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.url, "https://daotao.huce.edu.vn/thong-bao-2")
        self.assertFalse(args.skip_media)
        self.assertIsNone(args.output_dir)
