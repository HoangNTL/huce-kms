import json
import logging
from pathlib import Path
from typing import Any

from api.core.config import settings
from api.services.crawler.deduplicator import Deduplicator
from api.services.crawler.schemas import PageMetadata
from api.services.crawler.utils import atomic_write_text

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
        atomic_write_text(content_path, markdown_content)

        # 2. Write raw.html
        raw_path = page_dir / "raw.html"
        atomic_write_text(raw_path, raw_html)

        # 3. Write metadata.json
        meta_path = page_dir / "metadata.json"
        atomic_write_text(meta_path, metadata.model_dump_json(indent=2))

        logger.info("Saved page artifacts to: %s", page_dir)
        return page_dir

    def save_session(
        self,
        session_id: str,
        session_info: dict[str, Any],
        results: list[dict[str, Any]] | None = None,
    ) -> Path:
        """Persist session summary and optionally itemized results to sessions/<session_id>/."""
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        session_file = session_dir / "session.json"
        atomic_write_text(session_file, json.dumps(session_info, indent=2, ensure_ascii=False))

        if results is not None:
            results_file = session_dir / "results.json"
            atomic_write_text(results_file, json.dumps(results, indent=2, ensure_ascii=False))

        return session_dir
