import math
from typing import Generic, TypeVar
from pydantic import BaseModel, Field

DataType = TypeVar("DataType")


class PaginationMeta(BaseModel):
    """Detailed pagination metadata for client consumption."""

    total: int = Field(..., description="Total records matching criteria")
    skip: int = Field(..., description="Number of skipped records")
    limit: int = Field(..., description="Maximum records per page")
    page: int = Field(..., description="Current page index (1-based)")
    total_pages: int = Field(..., description="Total available pages")

    @classmethod
    def create(cls, total: int, skip: int, limit: int) -> "PaginationMeta":
        page = (skip // limit) + 1 if limit > 0 else 1
        total_pages = math.ceil(total / limit) if limit > 0 else 1
        return cls(
            total=total,
            skip=skip,
            limit=limit,
            page=page,
            total_pages=total_pages,
        )


class PaginatedData(BaseModel, Generic[DataType]):
    """Generic envelope for paginated lists with metadata."""

    items: list[DataType]
    pagination: PaginationMeta


class BaseResponse(BaseModel, Generic[DataType]):
    """Standardized response envelope across the entire API."""

    success: bool = Field(default=True, description="Execution success indicator")
    code: str = Field(default="SUCCESS", description="Application status code")
    message: str = Field(default="Operation completed successfully", description="User-facing summary message")
    data: DataType | None = Field(default=None, description="Response payload")
