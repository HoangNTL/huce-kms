from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Path, status

from api.core.dependencies import AdminUserDep, DatabaseDep
from api.repositories.category import CategoryRepository
from api.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from api.schemas.common import BaseResponse
from api.services.category import CategoryService

router = APIRouter()


def get_category_service(db: DatabaseDep) -> CategoryService:
    category_repo = CategoryRepository(db)
    return CategoryService(category_repo)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


@router.get(
    "/",
    response_model=BaseResponse[list[CategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all document categories",
)
async def list_categories(service: CategoryServiceDep):
    categories = await service.list_categories()
    return BaseResponse(
        message="Categories retrieved successfully.",
        data=list(categories),
    )


@router.get(
    "/{category_id}",
    response_model=BaseResponse[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get category details by ID",
)
async def get_category(
    category_id: Annotated[UUID, Path(description="Category unique identifier")],
    service: CategoryServiceDep,
):
    category = await service.get_category_by_id(category_id)
    return BaseResponse(
        message="Category details retrieved successfully.",
        data=category,
    )


@router.post(
    "/",
    response_model=BaseResponse[CategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new document category (Admin only)",
)
async def create_category(
    payload: CategoryCreate,
    admin_user: AdminUserDep,
    service: CategoryServiceDep,
):
    category = await service.create_category(payload)
    return BaseResponse(
        code="CATEGORY_CREATED",
        message="Category created successfully.",
        data=category,
    )


@router.patch(
    "/{category_id}",
    response_model=BaseResponse[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update document category (Admin only)",
)
async def update_category(
    category_id: Annotated[UUID, Path(description="Category unique identifier")],
    payload: CategoryUpdate,
    admin_user: AdminUserDep,
    service: CategoryServiceDep,
):
    category = await service.update_category(category_id, payload)
    return BaseResponse(
        message="Category updated successfully.",
        data=category,
    )


@router.delete(
    "/{category_id}",
    response_model=BaseResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete document category (Admin only)",
)
async def delete_category(
    category_id: Annotated[UUID, Path(description="Category unique identifier")],
    admin_user: AdminUserDep,
    service: CategoryServiceDep,
):
    await service.delete_category(category_id)
    return BaseResponse(
        message="Category deleted successfully.",
        data=None,
    )
