import re
import unicodedata
from collections.abc import Sequence
from uuid import UUID

from api.core.exceptions import ConflictException, EntityNotFoundException
from api.models.category import Category
from api.repositories.category import CategoryRepository
from api.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate


def slugify(text: str) -> str:
    """Generate URL-safe slug supporting Vietnamese characters."""
    text = text.replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


class CategoryService:
    """Business logic service for document categories."""

    def __init__(self, category_repo: CategoryRepository):
        self.category_repo = category_repo

    async def list_categories(self) -> Sequence[CategoryResponse]:
        categories = await self.category_repo.list_all()
        return [CategoryResponse.model_validate(c) for c in categories]

    async def get_category_by_id(self, category_id: UUID) -> CategoryResponse:
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise EntityNotFoundException(entity_name="Category", entity_id=category_id)
        return CategoryResponse.model_validate(category)

    async def get_category_by_slug(self, slug: str) -> CategoryResponse:
        category = await self.category_repo.get_by_slug(slug)
        if not category:
            raise EntityNotFoundException(
                entity_name="Category",
                message=f"Category with slug '{slug}' not found.",
            )
        return CategoryResponse.model_validate(category)

    async def create_category(self, payload: CategoryCreate) -> CategoryResponse:
        slug = payload.slug or slugify(payload.name)

        # Check for unique name and slug
        if await self.category_repo.get_by_name(payload.name):
            raise ConflictException(
                message=f"Category with name '{payload.name}' already exists."
            )
        if await self.category_repo.get_by_slug(slug):
            raise ConflictException(
                message=f"Category with slug '{slug}' already exists."
            )

        category = Category(
            name=payload.name,
            slug=slug,
            description=payload.description,
        )
        created = await self.category_repo.create(category)
        return CategoryResponse.model_validate(created)

    async def update_category(self, category_id: UUID, payload: CategoryUpdate) -> CategoryResponse:
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise EntityNotFoundException(entity_name="Category", entity_id=category_id)

        if payload.name is not None and payload.name != category.name:
            if await self.category_repo.get_by_name(payload.name):
                raise ConflictException(
                    message=f"Category with name '{payload.name}' already exists."
                )
            category.name = payload.name

        if payload.slug is not None and payload.slug != category.slug:
            if await self.category_repo.get_by_slug(payload.slug):
                raise ConflictException(
                    message=f"Category with slug '{payload.slug}' already exists."
                )
            category.slug = payload.slug

        if payload.description is not None:
            category.description = payload.description

        updated = await self.category_repo.update(category)
        return CategoryResponse.model_validate(updated)

    async def delete_category(self, category_id: UUID) -> None:
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise EntityNotFoundException(entity_name="Category", entity_id=category_id)
        await self.category_repo.delete(category)
