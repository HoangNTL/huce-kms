import unittest
from pathlib import Path
from tools.crawler.cli import build_parser


class TestCLIIngest(unittest.TestCase):
    def test_ingest_page_subcommand_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "ingest",
            "--page",
            "data/crawled/pages/123abc456",
            "--category-id",
            "5",
        ])
        self.assertEqual(args.command, "ingest")
        self.assertEqual(args.page.as_posix(), "data/crawled/pages/123abc456")
        self.assertEqual(args.category_id, 5)
        self.assertFalse(args.auto_publish)

    def test_ingest_session_auto_publish_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "ingest",
            "--session",
            "data/crawled/sessions/2026-11-10_001",
            "--auto-publish",
        ])
        self.assertEqual(args.command, "ingest")
        self.assertEqual(args.session.as_posix(), "data/crawled/sessions/2026-11-10_001")
        self.assertTrue(args.auto_publish)
