import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.core.config import settings
from api.services.crawler.discovery.schemas import DiscoveryResult
from api.services.crawler.registry.schemas import ApprovedQueue

logger = logging.getLogger(__name__)


class ReviewQueueManager:
    """Manages discovery results queue and human approval workflows."""

    def __init__(self, queue_dir: Path | None = None):
        self.queue_dir = queue_dir or (Path(settings.CRAWLER_DATA_DIR) / "crawl-queue")
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def save_discovered(self, result: DiscoveryResult, filename: str | None = None) -> Path:
        """Persist a DiscoveryResult into the queue folder."""
        if not filename:
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"discovered_{ts}.json"

        target_path = self.queue_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        logger.info(f"Saved {result.total_discovered} discovered items to: {target_path}")
        return target_path

    def approve_items(
        self,
        discovered_file: Path,
        approved_urls: list[str] | None = None,
        approve_indices: list[int] | None = None,
        approve_all: bool = False,
        output_file: Path | None = None,
    ) -> Path:
        """Filter discovered items by approval criteria and save to approved queue file."""
        with open(discovered_file, "r", encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)

        raw_items: list[dict[str, Any]] = data.get("items", [])
        final_urls: list[str] = []

        if approve_all:
            final_urls = [item["url"] for item in raw_items if "url" in item]
        else:
            if approved_urls:
                approved_set = set(approved_urls)
                final_urls.extend([item["url"] for item in raw_items if item.get("url") in approved_set])

            if approve_indices:
                for idx in approve_indices:
                    # Support 1-based indexing if >= 1
                    target_idx = idx - 1 if idx >= 1 else idx
                    if 0 <= target_idx < len(raw_items):
                        u = raw_items[target_idx].get("url")
                        if u and u not in final_urls:
                            final_urls.append(u)

        queue = ApprovedQueue(
            total_urls=len(final_urls),
            urls=final_urls,
        )

        out_path = output_file or (self.queue_dir / "approved.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(queue.model_dump_json(indent=2))

        logger.info(f"Approved {len(final_urls)} URLs written to: {out_path}")
        return out_path

    def load_approved_urls(self, approved_file: Path) -> list[str]:
        """Load list of approved URLs from approved.json or raw JSON."""
        with open(approved_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return [str(u) for u in data]

        if isinstance(data, dict):
            if "urls" in data and isinstance(data["urls"], list):
                return [str(u) for u in data["urls"]]

        raise ValueError(f"Invalid approved file format in: {approved_file}")
