import asyncio
from collections.abc import Awaitable, Callable
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from api.core.config import settings
from api.services.crawler.core.extractor import HtmlExtractor
from api.services.crawler.core.fetcher import HttpFetcher
from api.services.crawler.core.file_downloader import FileDownloader
from api.services.crawler.core.html_cleaner import HtmlCleaner
from api.services.crawler.core.link_discoverer import LinkDiscoverer
from api.services.crawler.core.markdown_converter import MarkdownConverter
from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.schemas import (
    BatchCrawlResult,
    CrawledMediaItem,
    CrawlResult,
    PageContentMeta,
    PageCrawlStatus,
    PageMediaMeta,
    PageMetadata,
    PageSourceMeta,
)
from api.services.crawler.storage.artifact_storage import ArtifactStorage

logger = logging.getLogger("huce_kms.crawler.engine")


class CrawlerCoreEngine:
    """Orchestrates single-URL fetch, media extraction, boilerplate cleaning, conversion and artifact storage."""

    def __init__(
        self,
        base_data_dir: Path | None = None,
        allowed_domains: list[str] | None = None,
        check_dns: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.fetcher = HttpFetcher(
            allowed_domains=allowed_domains,
            check_dns=check_dns,
            transport=transport,
        )
        self.storage = ArtifactStorage(base_dir=base_data_dir)
        self.check_dns = check_dns

    async def crawl_url(
        self,
        url: str,
        skip_media: bool = False,
        session_id: str | None = None,
    ) -> CrawlResult:
        """Execute full crawl pipeline for a single target URL."""
        start_time = time.perf_counter()
        errors: list[str] = []

        # 1. Fetch raw HTML
        fetch_res = await self.fetcher.fetch_html(url)
        raw_html = fetch_res.html
        final_url = fetch_res.final_url
        domain = urlsplit(final_url).netloc.lower()

        # 2. Extract metadata (title, publish date)
        extracted_meta = HtmlExtractor.extract_metadata(raw_html, final_url)
        title = extracted_meta.title

        # 3. Clean boilerplate and isolate main content
        cleaned_res = HtmlCleaner.clean_and_isolate_content(raw_html, final_url)

        # 4. Discover media links (PDFs and genuine content images)
        discovered_media = LinkDiscoverer.discover(cleaned_res.soup, final_url)

        # 5. Prepare page directory
        page_dir = self.storage.prepare_page_dir(url)
        pdfs_dir = page_dir / "pdfs"
        images_dir = page_dir / "images"

        # 6. Download media attachments
        crawled_pdfs: list[CrawledMediaItem] = []
        crawled_images: list[CrawledMediaItem] = []
        media_mapping: dict[str, str] = {}

        if not skip_media:
            headers = {"User-Agent": self.fetcher.user_agent}
            client_kwargs = {
                "timeout": httpx.Timeout(self.fetcher.timeout),
                "headers": headers,
            }
            if self.fetcher.transport is not None:
                client_kwargs["transport"] = self.fetcher.transport

            async with httpx.AsyncClient(**client_kwargs) as client:
                # Download PDFs
                for link in discovered_media.pdfs:
                    try:
                        res = await FileDownloader.download_file_stream(
                            client=client,
                            url=link.url,
                            dest_dir=pdfs_dir,
                            media_type="pdf",
                            preferred_name=link.title,
                            url_validator=self.fetcher.validate_url,
                        )
                        crawled_pdfs.append(
                            CrawledMediaItem(
                                url=link.url,
                                local_path=f"pdfs/{res.file_name}",
                                file_name=res.file_name,
                                file_size=res.file_size,
                                file_hash=res.file_hash,
                                mime_type=res.mime_type,
                                media_type="pdf",
                                status="success",
                            )
                        )
                        media_mapping[link.url] = f"./pdfs/{res.file_name}"
                    except Exception as e:
                        err_msg = f"Failed to download PDF '{link.url}': {e}"
                        logger.warning(err_msg)
                        errors.append(err_msg)
                        crawled_pdfs.append(
                            CrawledMediaItem(
                                url=link.url,
                                local_path="",
                                file_name="",
                                file_size=0,
                                file_hash="",
                                mime_type="",
                                media_type="pdf",
                                status="failed",
                                error=str(e),
                            )
                        )

                # Download Images
                for img_link in discovered_media.images:
                    try:
                        res = await FileDownloader.download_file_stream(
                            client=client,
                            url=img_link.url,
                            dest_dir=images_dir,
                            media_type="image",
                            url_validator=self.fetcher.validate_url,
                        )
                        crawled_images.append(
                            CrawledMediaItem(
                                url=img_link.url,
                                local_path=f"images/{res.file_name}",
                                file_name=res.file_name,
                                file_size=res.file_size,
                                file_hash=res.file_hash,
                                mime_type=res.mime_type,
                                media_type="image",
                                status="success",
                            )
                        )
                        media_mapping[img_link.url] = f"./images/{res.file_name}"
                    except Exception as e:
                        err_msg = f"Failed to download image '{img_link.url}': {e}"
                        logger.warning(err_msg)
                        errors.append(err_msg)
                        crawled_images.append(
                            CrawledMediaItem(
                                url=img_link.url,
                                local_path="",
                                file_name="",
                                file_size=0,
                                file_hash="",
                                mime_type="",
                                media_type="image",
                                status="failed",
                                error=str(e),
                            )
                        )

        # 7. Convert HTML to clean Markdown with local media rewrites
        crawled_at = datetime.now(timezone.utc).isoformat()
        markdown_content = MarkdownConverter.convert(
            html=str(cleaned_res.soup),
            title=title,
            source_url=final_url,
            crawled_at=crawled_at,
            published_at=extracted_meta.published_at,
            media_mapping=media_mapping,
        )

        # Append explicit attachments section for downloaded PDFs
        successful_pdf_items = [p for p in crawled_pdfs if p.status == "success"]
        if successful_pdf_items:
            pdf_section = ["\n\n## Tài liệu đính kèm\n"]
            for p in successful_pdf_items:
                pdf_section.append(f"- [{p.file_name}](./{p.local_path})")
            markdown_content += "\n".join(pdf_section)

        # Note: OCR enrichment for scanned images is deferred to the Ingestion phase
        # to ensure fast crawling speeds, avoid API timeout, and prevent quota waste on discarded drafts.
        content_hash = Deduplicator.compute_content_hash(markdown_content)

        # 8. Create PageMetadata manifest
        crawl_status = "success"
        if errors and (len(crawled_pdfs) + len(crawled_images) > len(errors)):
            crawl_status = "partial"
        elif errors and not crawled_pdfs and not crawled_images:
            crawl_status = "partial"

        metadata = PageMetadata(
            source=PageSourceMeta(
                url=url,
                canonical_url=final_url,
                domain=domain,
            ),
            content=PageContentMeta(
                title=title,
                published_at=extracted_meta.published_at,
                crawled_at=crawled_at,
                markdown_file="content.md",
                content_hash=content_hash,
            ),
            media=PageMediaMeta(
                pdfs=crawled_pdfs,
                images=crawled_images,
            ),
            crawl=PageCrawlStatus(
                status=crawl_status,
                http_status=fetch_res.status_code,
                error_message="; ".join(errors) if errors else None,
            ),
        )

        # 9. Save artifacts to disk
        self.storage.save_page(
            url=url,
            metadata=metadata,
            raw_html=raw_html,
            markdown_content=markdown_content,
        )

        duration = round(time.perf_counter() - start_time, 2)
        successful_pdfs = sum(1 for p in crawled_pdfs if p.status == "success")
        successful_images = sum(1 for img in crawled_images if img.status == "success")

        return CrawlResult(
            url=url,
            status=crawl_status,
            title=title,
            page_hash=page_dir.name,
            artifact_dir=page_dir,
            markdown_path=page_dir / "content.md",
            metadata_path=page_dir / "metadata.json",
            pdf_count=successful_pdfs,
            image_count=successful_images,
            duration_seconds=duration,
            errors=errors,
        )

    async def crawl_batch(
        self,
        urls: list[str],
        max_concurrency: int = 2,
        skip_media: bool = False,
        session_id: str | None = None,
        on_item_completed: Callable[[CrawlResult, int, int], Awaitable[None]] | None = None,
    ) -> BatchCrawlResult:
        """Crawl a batch of URLs with bounded concurrency, real-time progress callbacks, and session record keeping."""
        started_at = datetime.now(timezone.utc).isoformat()
        start_time = time.perf_counter()
        active_session_id = session_id or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")

        # Initial in-progress session record
        initial_session_info = {
            "session_id": active_session_id,
            "status": "in_progress",
            "started_at": started_at,
            "completed_at": None,
            "duration_seconds": 0.0,
            "total_urls": len(urls),
            "completed_urls": 0,
            "successful": 0,
            "failed": 0,
        }
        self.storage.save_session(active_session_id, initial_session_info, [])

        semaphore = asyncio.Semaphore(max_concurrency)
        results: list[CrawlResult] = []
        progress_lock = asyncio.Lock()
        completed_count = 0
        successful_count = 0
        failed_count = 0

        async def _crawl_single(target_url: str) -> CrawlResult:
            nonlocal completed_count, successful_count, failed_count
            async with semaphore:
                try:
                    res = await self.crawl_url(
                        url=target_url,
                        skip_media=skip_media,
                        session_id=active_session_id,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error("Failed crawling %s in batch: %s", target_url, exc, exc_info=True)
                    page_dir = self.storage.get_page_dir(target_url)
                    res = CrawlResult(
                        url=target_url,
                        status="failed",
                        title=target_url,
                        artifact_dir=page_dir,
                        duration_seconds=0.0,
                        errors=[str(exc)],
                    )

                async with progress_lock:
                    results.append(res)
                    completed_count += 1
                    if res.status in ("success", "partial"):
                        successful_count += 1
                    else:
                        failed_count += 1

                    # Realtime progress update on disk (lightweight session.json only)
                    prog_info = {
                        "session_id": active_session_id,
                        "status": "in_progress",
                        "started_at": started_at,
                        "completed_at": None,
                        "duration_seconds": round(time.perf_counter() - start_time, 2),
                        "total_urls": len(urls),
                        "completed_urls": completed_count,
                        "successful": successful_count,
                        "failed": failed_count,
                    }
                    self.storage.save_session(active_session_id, prog_info, results=None)

                if on_item_completed:
                    try:
                        await on_item_completed(res, completed_count, len(urls))
                    except Exception as cb_err:
                        logger.warning("Error in on_item_completed callback: %s", cb_err)

                return res

        tasks = [asyncio.create_task(_crawl_single(u)) for u in urls]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.warning("Batch crawl session '%s' received cancellation signal.", active_session_id)
            for t in tasks:
                if not t.done():
                    t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

            # Save cancelled snapshot on disk
            cancelled_info = {
                "session_id": active_session_id,
                "status": "cancelled",
                "started_at": started_at,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": round(time.perf_counter() - start_time, 2),
                "total_urls": len(urls),
                "completed_urls": completed_count,
                "successful": successful_count,
                "failed": failed_count,
            }
            self.storage.save_session(
                active_session_id,
                cancelled_info,
                [r.model_dump(mode="json") for r in results],
            )
            raise

        completed_at = datetime.now(timezone.utc).isoformat()
        duration_seconds = round(time.perf_counter() - start_time, 2)

        session_info = {
            "session_id": active_session_id,
            "status": "completed",
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": duration_seconds,
            "total_urls": len(urls),
            "completed_urls": completed_count,
            "successful": successful_count,
            "failed": failed_count,
        }
        item_results = [r.model_dump(mode="json") for r in results]
        self.storage.save_session(active_session_id, session_info, item_results)

        return BatchCrawlResult(
            session_id=active_session_id,
            total_urls=len(urls),
            successful=successful_count,
            failed=failed_count,
            started_at=started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            results=results,
        )
