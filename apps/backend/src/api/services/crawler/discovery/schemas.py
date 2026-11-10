from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field


class DiscoveredItem(BaseModel):
    """Represents a potential article URL discovered from a listing page or feed."""

    url: str
    title: str
    published_at: str | None = None
    summary: str | None = None
    thumbnail_url: str | None = None
    status: Literal["discovered", "approved", "rejected", "crawled"] = "discovered"


class DiscoveryResult(BaseModel):
    """Aggregate output from running discovery on a listing page or feed."""

    source_url: str
    discovered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_discovered: int
    items: list[DiscoveredItem] = Field(default_factory=list)
