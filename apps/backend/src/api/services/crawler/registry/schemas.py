from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ApprovedQueue(BaseModel):
    """Schema for approved URL batch ready for crawling."""

    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_urls: int
    urls: list[str] = Field(default_factory=list)
