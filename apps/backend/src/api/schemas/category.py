from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["Academic Regulations"])
    slug: str = Field(..., min_length=2, max_length=100, examples=["academic-regulations"])
    description: str | None = Field(default=None, max_length=255, examples=["General academic regulations and guidelines"])


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["Academic Regulations"])
    slug: str | None = Field(default=None, min_length=2, max_length=100, examples=["academic-regulations"])
    description: str | None = Field(default=None, max_length=255, examples=["General academic regulations and guidelines"])


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class CategoryResponse(CategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
