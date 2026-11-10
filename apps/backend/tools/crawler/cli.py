import argparse
import asyncio
import logging
import sys
from pathlib import Path

from api.services.crawler.core.engine import CrawlerCoreEngine
from api.services.crawler.discovery.engine import DiscoveryEngine
from api.services.crawler.exceptions import CrawlerException
from api.services.crawler.registry.review_queue import ReviewQueueManager


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for HUCE Crawler CLI."""
    parser = argparse.ArgumentParser(
        prog="huce-crawler",
        description="HUCE-KMS Controlled Content Crawler (CLI Runner)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. DISCOVERY Mode: discover candidate URLs from listing or feed
    disc_parser = subparsers.add_parser(
        "discover",
        help="Discover candidate article URLs from category listing, sitemap or RSS (DISCOVERY Mode)",
    )
    disc_parser.add_argument(
        "--url",
        "-u",
        required=True,
        type=str,
        help="Category listing or sitemap/feed URL (e.g. https://ctsv.huce.edu.vn/quy-che-quy-dinh)",
    )
    disc_parser.add_argument(
        "--max-items",
        "-m",
        type=int,
        default=50,
        help="Maximum candidate items to discover (default: 50)",
    )
    disc_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Target JSON file path to store discovered items",
    )
    disc_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )

    # 2. APPROVE Mode: human review and approve candidate items
    appr_parser = subparsers.add_parser(
        "approve",
        help="Review discovered URLs and generate approved queue for crawling",
    )
    appr_parser.add_argument(
        "--input",
        "-i",
        required=True,
        type=Path,
        help="Path to discovered JSON file (e.g. data/crawl-queue/discovered_*.json)",
    )
    appr_parser.add_argument(
        "--all",
        action="store_true",
        help="Approve all discovered items in the file",
    )
    appr_parser.add_argument(
        "--indices",
        type=str,
        default=None,
        help="Comma-separated 1-based indices to approve (e.g. 1,2,5)",
    )
    appr_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output JSON file path for approved URLs (default: data/crawl-queue/approved.json)",
    )

    # 3. CRAWL Mode: DIRECT (single URL) or APPROVED (batch input)
    crawl_parser = subparsers.add_parser(
        "crawl",
        help="Crawl single URL (DIRECT) or batch of approved URLs (APPROVED Mode)",
    )
    crawl_group = crawl_parser.add_mutually_exclusive_group(required=True)
    crawl_group.add_argument(
        "--url",
        "-u",
        type=str,
        help="Target single article URL to crawl (DIRECT Mode)",
    )
    crawl_group.add_argument(
        "--input",
        "-i",
        type=Path,
        help="Path to approved URLs JSON file (APPROVED Mode)",
    )
    crawl_parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=2,
        help="Maximum concurrent crawl workers for batch mode (default: 2)",
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

    # 4. INGEST Mode: Ingest crawled pages/sessions into RAG pipeline
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest crawled artifacts into PostgreSQL and optionally Vector DB (INGEST Mode)",
    )
    ingest_group = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_group.add_argument(
        "--page",
        "-p",
        type=Path,
        help="Path to single crawled page artifact directory (e.g. data/crawled/pages/<hash>/)",
    )
    ingest_group.add_argument(
        "--session",
        "-s",
        type=Path,
        help="Path to crawled session directory (e.g. data/crawled/sessions/<session_id>/)",
    )
    ingest_parser.add_argument(
        "--category-id",
        type=int,
        default=None,
        help="Target category ID to associate with documents",
    )
    ingest_parser.add_argument(
        "--auto-publish",
        action="store_true",
        help="Directly parse, chunk, embed, and index into Vector DB (default: draft/uploaded mode)",
    )
    ingest_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )

    return parser


async def run_discover(args: argparse.Namespace) -> int:
    """Execute DISCOVERY mode."""
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    engine = DiscoveryEngine()
    queue_mgr = ReviewQueueManager()

    print("\n" + "=" * 80)
    print(" HUCE-KMS CONTENT CRAWLER — DISCOVERY MODE")
    print("=" * 80)
    print(f"[*] Target listing / feed: {args.url}")
    print(f"[*] Max items limit:       {args.max_items}")

    try:
        res = await engine.discover(args.url, max_items=args.max_items)
        out_filename = args.output.name if args.output else None
        saved_path = queue_mgr.save_discovered(res, filename=out_filename)

        print("\n" + "-" * 80)
        print(" DISCOVERY COMPLETE")
        print("-" * 80)
        print(f"Total Discovered: {res.total_discovered} item(s)")
        print(f"Saved Queue File: {saved_path}")
        print("\nCandidate Articles:")
        for idx, item in enumerate(res.items, start=1):
            date_str = f" ({item.published_at})" if item.published_at else ""
            print(f"  [{idx:2d}] {item.title}{date_str}")
            print(f"       -> {item.url}")

        print("\nTo approve items for crawl, run:")
        print(f"  uv run python -m tools.crawler.cli approve --input \"{saved_path}\" --indices 1,2")
        print(f"  or approve all: uv run python -m tools.crawler.cli approve --input \"{saved_path}\" --all")
        print("=" * 80 + "\n")
        return 0
    except CrawlerException as ce:
        print(f"\n[X] Crawler Domain Error: {ce.message}")
        if ce.details:
            print(f"    Details: {ce.details}")
        print("=" * 80 + "\n")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected Error during discovery: {e}")
        print("=" * 80 + "\n")
        return 1
    finally:
        await engine.aclose()


def run_approve(args: argparse.Namespace) -> int:
    """Execute APPROVE mode."""
    queue_mgr = ReviewQueueManager()

    print("\n" + "=" * 80)
    print(" HUCE-KMS CONTENT CRAWLER — APPROVAL QUEUE")
    print("=" * 80)
    print(f"[*] Input discovered queue: {args.input}")

    indices: list[int] | None = None
    if args.indices:
        try:
            indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
        except ValueError:
            print("[X] Error: --indices must be comma-separated integers (e.g. 1,2,5)")
            return 1

    try:
        approved_path = queue_mgr.approve_items(
            discovered_file=args.input,
            approve_indices=indices,
            approve_all=args.all,
            output_file=args.output,
        )
        approved_urls = queue_mgr.load_approved_urls(approved_path)

        print("\n" + "-" * 80)
        print(" APPROVAL COMPLETE")
        print("-" * 80)
        print(f"Total Approved:   {len(approved_urls)} URL(s)")
        print(f"Approved File:    {approved_path}")
        for idx, u in enumerate(approved_urls, start=1):
            print(f"  [{idx:2d}] {u}")

        print("\nTo execute crawl for approved URLs, run:")
        print(f"  uv run python -m tools.crawler.cli crawl --input \"{approved_path}\" --concurrency 2")
        print("=" * 80 + "\n")
        return 0
    except Exception as e:
        print(f"\n[X] Error during approval: {e}")
        print("=" * 80 + "\n")
        return 1


async def run_crawl(args: argparse.Namespace) -> int:
    """Execute DIRECT mode single-URL crawl or APPROVED mode batch crawl."""
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    engine = CrawlerCoreEngine(base_data_dir=args.output_dir)

    # 1. DIRECT Mode: single URL
    if args.url:
        print("\n" + "=" * 80)
        print(" HUCE-KMS CONTENT CRAWLER — DIRECT MODE")
        print("=" * 80)
        print(f"[*] Starting crawl for: {args.url}")
        if args.skip_media:
            print("[*] Media download: DISABLED (--skip-media)")
        else:
            print("[*] Media download: ENABLED (PDFs & Images will be downloaded locally)")

        try:
            result = await engine.crawl_url(url=args.url, skip_media=args.skip_media)
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

    # 2. APPROVED Mode: batch URLs from input file
    if args.input:
        queue_mgr = ReviewQueueManager()
        try:
            urls = queue_mgr.load_approved_urls(args.input)
        except Exception as e:
            print(f"[X] Failed to read approved URLs from {args.input}: {e}")
            return 1

        print("\n" + "=" * 80)
        print(" HUCE-KMS CONTENT CRAWLER — APPROVED BATCH MODE")
        print("=" * 80)
        print(f"[*] Approved input file: {args.input}")
        print(f"[*] Total target URLs:   {len(urls)}")
        print(f"[*] Worker concurrency:  {args.concurrency}")
        if args.skip_media:
            print("[*] Media download:      DISABLED (--skip-media)")
        else:
            print("[*] Media download:      ENABLED (PDFs & Images)")

        batch_res = await engine.crawl_batch(
            urls=urls,
            max_concurrency=args.concurrency,
            skip_media=args.skip_media,
        )

        print("\n" + "-" * 80)
        print(" BATCH CRAWL COMPLETE")
        print("-" * 80)
        print(f"Session ID:       {batch_res.session_id}")
        print(f"Total Processed:  {batch_res.total_urls}")
        print(f"Successful:       {batch_res.successful}")
        print(f"Failed:           {batch_res.failed}")
        print(f"Total Duration:   {batch_res.duration_seconds}s")
        print("\nItemized Results:")
        for idx, r in enumerate(batch_res.results, start=1):
            status_tag = f"[{r.status.upper():7s}]"
            print(f"  {idx:2d}. {status_tag} {r.title}")
            print(f"      URL: {r.url}")
            print(f"      PDFs: {r.pdf_count}, Images: {r.image_count}")
            if r.errors:
                print(f"      Errors: {', '.join(r.errors)}")

        print(f"\nSession artifacts saved in: data/crawled/sessions/{batch_res.session_id}/")
        print("=" * 80 + "\n")
        return 0 if batch_res.failed == 0 else 1

    return 1


async def run_ingest(args: argparse.Namespace) -> int:
    """Execute INGEST mode into PostgreSQL and optionally Qdrant."""
    from api.core.database import async_session_factory
    from api.repositories.category import CategoryRepository
    from api.repositories.document import DocumentRepository
    from api.repositories.document_chunk import DocumentChunkRepository
    from api.services.crawler.ingestion.adapter import CrawlIngestionAdapter
    from api.services.document import DocumentService
    from api.services.rag.embedder import GeminiEmbeddingService
    from api.services.rag.vector_store import QdrantVectorStore

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    mode_str = "AUTO-PUBLISH (INDEX TO QDRANT)" if args.auto_publish else "STAGING / DRAFT (POSTGRES ONLY)"
    print("\n" + "=" * 80)
    print(" HUCE-KMS CONTENT CRAWLER — RAG INGESTION PIPELINE")
    print("=" * 80)
    print(f"[*] Ingestion Mode: {mode_str}")
    if args.category_id:
        print(f"[*] Category ID:    {args.category_id}")

    async with async_session_factory() as session:
        doc_repo = DocumentRepository(session)
        chunk_repo = DocumentChunkRepository(session)
        cat_repo = CategoryRepository(session)
        embedder = GeminiEmbeddingService()
        vector_store = QdrantVectorStore()

        doc_service = DocumentService(
            document_repo=doc_repo,
            chunk_repo=chunk_repo,
            category_repo=cat_repo,
            embedder=embedder,
            vector_store=vector_store,
        )

        adapter = CrawlIngestionAdapter(
            document_service=doc_service,
            document_repo=doc_repo,
            category_repo=cat_repo,
        )

        try:
            if args.page:
                target_page = args.page
                if not target_page.exists():
                    print(f"[X] Error: Target page directory does not exist: {target_page}")
                    return 1

                print(f"[*] Ingesting single page: {target_page}")
                results = await adapter.ingest_page(
                    page_dir=target_page,
                    category_id=args.category_id,
                    auto_publish=args.auto_publish,
                )
                print("\n" + "-" * 80)
                print(" INGESTION COMPLETE")
                print("-" * 80)
                for idx, r in enumerate(results, start=1):
                    tag = f"[{r.status.upper():8s}]"
                    doc_id_str = f"ID: {r.document_id}" if r.document_id else "No ID"
                    chunks_str = f"({r.chunks_count} chunks)" if r.chunks_count else ""
                    print(f"  {idx:2d}. {tag} {r.title} ({r.file_type.upper()}) | {doc_id_str} {chunks_str}")
                    if r.error:
                        print(f"       Note: {r.error}")

            elif args.session:
                target_session = args.session
                if not target_session.exists():
                    alt = Path("data/crawled/sessions") / target_session
                    if alt.exists():
                        target_session = alt
                    else:
                        print(f"[X] Error: Target session directory does not exist: {target_session}")
                        return 1

                print(f"[*] Ingesting crawl session: {target_session}")
                summary = await adapter.ingest_session(
                    session_dir=target_session,
                    category_id=args.category_id,
                    auto_publish=args.auto_publish,
                )

                print("\n" + "-" * 80)
                print(" SESSION INGESTION COMPLETE")
                print("-" * 80)
                print(f"Pages Processed:   {summary.total_pages}")
                print(f"Total Documents:   {summary.total_documents}")
                print(f"Successful:        {summary.successful}")
                print(f"Skipped (Exists):  {summary.skipped}")
                print(f"Failed:            {summary.failed}")
                print("\nItemized Documents:")
                for idx, r in enumerate(summary.items, start=1):
                    tag = f"[{r.status.upper():8s}]"
                    doc_id_str = f"ID: {r.document_id}" if r.document_id else "No ID"
                    chunks_str = f"({r.chunks_count} chunks)" if r.chunks_count else ""
                    print(f"  {idx:2d}. {tag} {r.title} ({r.file_type.upper()}) | {doc_id_str} {chunks_str}")
                    if r.error:
                        print(f"       Note: {r.error}")

            await session.commit()
            print("=" * 80 + "\n")
            return 0

        except Exception as e:
            await session.rollback()
            print(f"\n[X] Error during ingestion: {e}")
            print("=" * 80 + "\n")
            return 1


def main() -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "discover":
        exit_code = asyncio.run(run_discover(args))
        sys.exit(exit_code)
    elif args.command == "approve":
        exit_code = run_approve(args)
        sys.exit(exit_code)
    elif args.command == "crawl":
        exit_code = asyncio.run(run_crawl(args))
        sys.exit(exit_code)
    elif args.command == "ingest":
        exit_code = asyncio.run(run_ingest(args))
        sys.exit(exit_code)
    else:
        parser.print_help()
        sys.exit(1)



if __name__ == "__main__":
    main()
