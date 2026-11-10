import json
import logging
from pathlib import Path
from typing import Any

from api.services.crawler.exceptions import CrawlerException
from api.services.crawler.ingestion.schemas import IngestPagePayload
from api.services.crawler.schemas import PageMetadata

logger = logging.getLogger(__name__)


class CrawlArtifactReader:
    """Reads crawl artifact directories (single page or whole session) into structured payloads."""

    @classmethod
    def read_page(cls, page_dir: Path) -> IngestPagePayload:
        """Inspect and parse a single page artifact folder."""
        meta_file = page_dir / "metadata.json"
        if not meta_file.exists():
            raise CrawlerException(f"Missing metadata.json in artifact directory: {page_dir}")

        with open(meta_file, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)

        metadata = PageMetadata.model_validate(meta_dict)

        content_file = page_dir / "content.md"
        markdown_content = ""
        if content_file.exists():
            markdown_content = content_file.read_text(encoding="utf-8")

        pdf_files: list[Path] = []
        pdfs_dir = page_dir / "pdfs"
        if pdfs_dir.exists() and pdfs_dir.is_dir():
            pdf_files = sorted(list(pdfs_dir.glob("*.pdf")))

        return IngestPagePayload(
            page_dir=page_dir,
            metadata=metadata,
            markdown_content=markdown_content,
            pdf_files=pdf_files,
        )

    @classmethod
    def read_session(cls, session_dir: Path) -> list[IngestPagePayload]:
        """Parse results.json in a session folder and read all successfully crawled pages."""
        results_file = session_dir / "results.json"
        if not results_file.exists():
            raise CrawlerException(f"Missing results.json in session directory: {session_dir}")

        with open(results_file, "r", encoding="utf-8") as f:
            results_data: list[dict[str, Any]] = json.load(f)

        payloads: list[IngestPagePayload] = []
        for item in results_data:
            if item.get("status") in ("success", "partial"):
                art_dir_str = item.get("artifact_dir")
                if art_dir_str:
                    art_dir = Path(art_dir_str)
                    if art_dir.exists():
                        try:
                            payloads.append(cls.read_page(art_dir))
                        except Exception as e:
                            logger.warning("Could not read page payload from '%s': %s", art_dir, e)

        return payloads
