import argparse
import asyncio
import logging
import sys
from pathlib import Path

from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.exceptions import CrawlerException


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for HUCE Crawler CLI."""
    parser = argparse.ArgumentParser(
        prog="huce-crawler",
        description="HUCE-KMS Controlled Content Crawler (CLI Runner)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # DIRECT Mode: crawl a single specific URL
    crawl_parser = subparsers.add_parser("crawl", help="Crawl a specific article/document URL (DIRECT Mode)")
    crawl_parser.add_argument(
        "--url",
        "-u",
        required=True,
        type=str,
        help="Target article URL to crawl (e.g. https://ctsv.huce.edu.vn/...)",
    )
    crawl_parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Custom root directory to store crawl artifacts (default: data/crawled/)",
    )
    crawl_parser.add_argument(
        "--skip-media",
        action="store_true",
        help="Skip downloading attached PDFs and images (extract HTML to Markdown only)",
    )
    crawl_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )

    return parser


async def run_crawl(args: argparse.Namespace) -> int:
    """Execute DIRECT mode single-URL crawl and print human-readable summary."""
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    engine = CrawlerCoreEngine(base_data_dir=args.output_dir)

    print("\n" + "=" * 80)
    print(" HUCE-KMS CONTENT CRAWLER — DIRECT MODE")
    print("=" * 80)
    print(f"[*] Starting crawl for: {args.url}")
    if args.skip_media:
        print("[*] Media download: DISABLED (--skip-media)")
    else:
        print("[*] Media download: ENABLED (PDFs & Images will be downloaded locally)")

    try:
        result = await engine.crawl_url(
            url=args.url,
            skip_media=args.skip_media,
        )

        print("\n" + "-" * 80)
        print(" CRAWL EXECUTION COMPLETE")
        print("-" * 80)
        print(f"Target URL:    {result.url}")
        print(f"Title:         {result.title}")
        print(f"Status:        {result.status.upper()} ({result.duration_seconds}s)")
        print(f"Artifact Dir:  {result.artifact_dir}")
        print(f"├── Markdown:  {result.markdown_path.name if result.markdown_path else 'None'}")
        print(f"├── Metadata:  {result.metadata_path.name if result.metadata_path else 'None'}")
        print(f"├── PDFs:      {result.pdf_count} file(s)")
        print(f"└── Images:    {result.image_count} file(s)")

        if result.errors:
            print("\n[!] Warnings/Minor Errors encountered:")
            for err in result.errors:
                print(f"    - {err}")

        print("=" * 80 + "\n")
        return 0

    except CrawlerException as ce:
        print(f"\n[X] Crawler Domain Error: {ce.message}")
        if ce.details:
            print(f"    Details: {ce.details}")
        print("=" * 80 + "\n")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected Error during crawl: {e}")
        print("=" * 80 + "\n")
        return 1


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "crawl":
        exit_code = asyncio.run(run_crawl(args))
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
