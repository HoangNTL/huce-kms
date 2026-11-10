import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from api.services.crawler.core.extractor import HtmlExtractor
from api.services.crawler.core.fetcher import HttpFetcher
from api.services.crawler.core.file_downloader import FileDownloader
from api.services.crawler.core.html_cleaner import HtmlCleaner
from api.services.crawler.core.link_discoverer import LinkDiscoverer
from api.services.crawler.core.markdown_converter import MarkdownConverter
from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.schemas import (
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
                "follow_redirects": True,
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
            artifact_dir=page_dir,
            markdown_path=page_dir / "content.md",
            metadata_path=page_dir / "metadata.json",
            pdf_count=successful_pdfs,
            image_count=successful_images,
            duration_seconds=duration,
            errors=errors,
        )
