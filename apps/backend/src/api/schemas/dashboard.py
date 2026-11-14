from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    name: str
    status: str  # "healthy" | "degraded" | "down"
    latency_ms: float | None = None
    details: str | None = None


class DashboardStatsResponse(BaseModel):
    total_documents: int = Field(default=0, description="Total documents in knowledge base")
    total_chunks: int = Field(default=0, description="Total vector chunks indexed")
    total_users: int = Field(default=0, description="Total registered accounts")
    active_users: int = Field(default=0, description="Total active accounts")
    total_categories: int = Field(default=0, description="Total document categories")
    total_file_size_bytes: int = Field(default=0, description="Total storage bytes of documents")
    indexed_documents: int = Field(default=0, description="Total documents successfully indexed")
    services: list[ServiceStatus] = Field(default_factory=list, description="Platform infrastructure health")
