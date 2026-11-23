from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Path, Query, status

from api.core.dependencies import AdminUserDep, CurrentUserDep, DatabaseDep, PaginationDep
from api.core.exceptions import ForbiddenException
from api.repositories.refresh_token import RefreshTokenRepository
from api.repositories.user import UserRepository
from api.schemas.common import BaseResponse, PaginatedData
from api.schemas.user import (
    AdminUserCreate,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from api.services.user import UserService

router = APIRouter()


# Dependency Factory: Inject UserService into route handlers
def get_user_service(db: DatabaseDep) -> UserService:
    user_repo = UserRepository(db)
    refresh_token_repo = RefreshTokenRepository(db)
    return UserService(user_repo, refresh_token_repo)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


# User Management Endpoints
@router.post(
    "/",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user directly (Admin only)",
)
async def create_user(
    payload: AdminUserCreate,
    admin_user: AdminUserDep,
    service: UserServiceDep,
):
    user = await service.create_user_by_admin(payload)
    return BaseResponse(
        code="USER_CREATED",
        message="User account created successfully.",
        data=user,
    )


@router.get(
    "/",
    response_model=BaseResponse[PaginatedData[UserResponse]],
    status_code=status.HTTP_200_OK,
    summary="List users with pagination, search, and filters (Admin only)",
)
async def list_users(
    pagination: PaginationDep,
    admin_user: AdminUserDep,
    service: UserServiceDep,
    q: str | None = Query(None, max_length=50, description="Search by username, email, or full name"),
    role: str | None = Query(None, description="Filter by role ('user' or 'admin')"),
    is_active: bool | None = Query(None, description="Filter by active status (true/false)"),
):
    data = await service.list_users(
        q=q,
        role=role,
        is_active=is_active,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return BaseResponse(
        message="Users list retrieved successfully.",
        data=data,
    )


@router.get(
    "/me",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve profile of currently authenticated user",
)
async def get_current_user_profile(
    current_user: CurrentUserDep,
    service: UserServiceDep,
):
    user = await service.get_user_by_id(current_user.id)
    return BaseResponse(
        message="User profile retrieved successfully.",
        data=user,
    )


@router.get(
    "/{user_id}",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID (Admin or account owner)",
)
async def get_user(
    user_id: Annotated[UUID, Path(description="User unique identifier")],
    current_user: CurrentUserDep,
    service: UserServiceDep,
):
    if not current_user.is_admin and current_user.id != user_id:
        raise ForbiddenException(message="Access denied: You can only view your own account details.")

    user = await service.get_user_by_id(user_id)
    return BaseResponse(
        message="User details retrieved successfully.",
        data=user,
    )


@router.patch(
    "/{user_id}",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update user profile (Admin or account owner)",
)
async def update_user(
    user_id: Annotated[UUID, Path(description="User unique identifier")],
    payload: UserUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
):
    if not current_user.is_admin and current_user.id != user_id:
        raise ForbiddenException(message="Access denied: You can only update your own account.")

    updated_user = await service.update_user(user_id, payload)
    return BaseResponse(
        message="User profile updated successfully.",
        data=updated_user,
    )


@router.patch(
    "/{user_id}/status",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Activate or deactivate user account (Admin only)",
)
async def update_user_status(
    user_id: Annotated[UUID, Path(description="User unique identifier")],
    payload: UserStatusUpdate,
    admin_user: AdminUserDep,
    service: UserServiceDep,
):
    updated_user = await service.update_user_status(
        user_id=user_id,
        is_active=payload.is_active,
        admin_id=admin_user.id,
    )
    status_label = "activated" if payload.is_active else "deactivated"
    return BaseResponse(
        message=f"User {user_id} has been {status_label} successfully.",
        data=updated_user,
    )


@router.patch(
    "/{user_id}/role",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Change user role ('user' or 'admin') (Admin only)",
)
async def update_user_role(
    user_id: Annotated[UUID, Path(description="User unique identifier")],
    payload: UserRoleUpdate,
    admin_user: AdminUserDep,
    service: UserServiceDep,
):
    updated_user = await service.update_user_role(
        user_id=user_id,
        role=payload.role,
        admin_id=admin_user.id,
    )
    return BaseResponse(
        message=f"User {user_id} role updated to '{updated_user.role_name}' successfully.",
        data=updated_user,
    )
