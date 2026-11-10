import json
import logging
from pathlib import Path
from typing import Any

from api.core.config import settings
from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.schemas import PageMetadata

logger = logging.getLogger("huce_kms.crawler.storage")


class ArtifactStorage:
    """Manages filesystem layout and artifact persistence for crawled pages and sessions."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or settings.CRAWLER_DATA_DIR
        self.pages_dir = self.base_dir / "pages"
        self.sessions_dir = self.base_dir / "sessions"

    def get_page_dir(self, url: str) -> Path:
        """Derive the deterministic artifact path for an URL from its hash."""
        page_hash = Deduplicator.hash_url(url)
        return self.pages_dir / page_hash

    def prepare_page_dir(self, url: str) -> Path:
        """Create target page directory with pdfs/ and images/ subfolders."""
        page_dir = self.get_page_dir(url)
        (page_dir / "pdfs").mkdir(parents=True, exist_ok=True)
        (page_dir / "images").mkdir(parents=True, exist_ok=True)
        return page_dir

    def save_page(
        self,
        url: str,
        metadata: PageMetadata,
        raw_html: str,
        markdown_content: str,
    ) -> Path:
        """Persist content.md, metadata.json, and raw.html into page directory."""
        page_dir = self.prepare_page_dir(url)

        # 1. Write content.md
        content_path = page_dir / "content.md"
        content_path.write_text(markdown_content, encoding="utf-8")

        # 2. Write raw.html
        raw_path = page_dir / "raw.html"
        raw_path.write_text(raw_html, encoding="utf-8")

        # 3. Write metadata.json
        meta_path = page_dir / "metadata.json"
        meta_path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")

        logger.info("Saved page artifacts to: %s", page_dir)
        return page_dir

    def save_session(
        self,
        session_id: str,
        session_info: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> Path:
        """Persist session summary and itemized results to sessions/<session_id>/."""
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session_file = session_dir / "session.json"
        session_file.write_text(json.dumps(session_info, indent=2, ensure_ascii=False), encoding="utf-8")

        results_file = session_dir / "results.json"
        results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        return session_dir
