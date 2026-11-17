import unittest
from unittest.mock import MagicMock, patch

from tools.rag.cli import build_parser, handle_chunk


class TestRAGCLI(unittest.TestCase):
    """Test CLI argument parsing and handlers for tools/rag/cli.py."""

    def setUp(self):
        self.parser = build_parser()

    def test_parser_extract_subcommand(self):
        args = self.parser.parse_args(["extract", "--file", "sample.pdf", "--max-pages", "5"])
        self.assertEqual(args.command, "extract")
        self.assertEqual(str(args.file), "sample.pdf")
        self.assertEqual(args.max_pages, 5)

    def test_parser_chunk_subcommand(self):
        args = self.parser.parse_args([
            "chunk",
            "--text",
            "Sample content to chunk",
            "--strategy",
            "recursive",
            "--chunk-size",
            "600",
            "--chunk-overlap",
            "100",
        ])
        self.assertEqual(args.command, "chunk")
        self.assertEqual(args.strategy, "recursive")
        self.assertEqual(args.chunk_size, 600)
        self.assertEqual(args.chunk_overlap, 100)

    def test_parser_retrieve_subcommand(self):
        args = self.parser.parse_args([
            "retrieve",
            "--query",
            "Học phần là gì?",
            "--top-k",
            "5",
            "--show-prompt",
        ])
        self.assertEqual(args.command, "retrieve")
        self.assertEqual(args.query, "Học phần là gì?")
        self.assertEqual(args.top_k, 5)
        self.assertTrue(args.show_prompt)

    def test_parser_eval_subcommand(self):
        args = self.parser.parse_args([
            "eval",
            "--file",
            "document.pdf",
            "--query",
            "Tín chỉ là gì?",
            "--synthesis",
        ])
        self.assertEqual(args.command, "eval")
        self.assertEqual(str(args.file), "document.pdf")
        self.assertEqual(args.query, "Tín chỉ là gì?")
        self.assertTrue(args.synthesis)

    def test_handle_chunk_with_text(self):
        args = self.parser.parse_args([
            "chunk",
            "--text",
            "Điều 1. Phạm vi\nNội dung điều 1.",
            "--strategy",
            "legal_structural",
            "--title",
            "Văn bản kiểm thử",
        ])
        # Execution should complete without error
        handle_chunk(args)


if __name__ == "__main__":
    unittest.main()
