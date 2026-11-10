import unittest
from pathlib import Path
from tools.crawler.cli import build_parser


class TestCLIDiscovery(unittest.TestCase):
    def test_discover_subcommand_args(self):
        parser = build_parser()
        args = parser.parse_args(["discover", "--url", "https://ctsv.huce.edu.vn/quy-che", "--max-items", "20"])
        self.assertEqual(args.command, "discover")
        self.assertEqual(args.url, "https://ctsv.huce.edu.vn/quy-che")
        self.assertEqual(args.max_items, 20)

    def test_approve_subcommand_args(self):
        parser = build_parser()
        args = parser.parse_args(["approve", "--input", "data/crawl-queue/discovered.json", "--all"])
        self.assertEqual(args.command, "approve")
        self.assertEqual(args.input.as_posix(), "data/crawl-queue/discovered.json")
        self.assertTrue(args.all)

    def test_approve_subcommand_indices(self):
        parser = build_parser()
        args = parser.parse_args(["approve", "--input", "data/crawl-queue/discovered.json", "--indices", "1,2,5"])
        self.assertEqual(args.indices, "1,2,5")

    def test_crawl_subcommand_with_input_file(self):
        parser = build_parser()
        args = parser.parse_args(["crawl", "--input", "data/crawl-queue/approved.json", "--concurrency", "3"])
        self.assertEqual(args.command, "crawl")
        self.assertEqual(args.input.as_posix(), "data/crawl-queue/approved.json")
        self.assertEqual(args.concurrency, 3)
