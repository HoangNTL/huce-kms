from collections.abc import AsyncGenerator, Callable
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.database import async_session_factory
from api.core.exceptions import ForbiddenException, UnauthorizedException
from api.core.security import decode_access_token
from api.repositories.user import UserRepository


# -----------------------------------------------------------------------------
# 1. Reusable Pagination Dependency
# -----------------------------------------------------------------------------
class PaginationParams(BaseModel):
    """Reusable pagination query parameters for list endpoints."""

    skip: int
    limit: int


def get_pagination_params(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
) -> PaginationParams:
    """Extract and validate pagination query parameters."""
    return PaginationParams(skip=skip, limit=limit)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination_params)]


# -----------------------------------------------------------------------------
# 2. Database Session Lifecycle Dependency (with yield)
# -----------------------------------------------------------------------------
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an asynchronous database session per request lifecycle:
    - Automatically commits transaction on successful execution.
    - Automatically rolls back transaction if an unhandled exception occurs.
    - Always closes session and releases connection in the finally block.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DatabaseDep = Annotated[AsyncSession, Depends(get_db_session)]


# -----------------------------------------------------------------------------
# 3. Authentication & Role-Based Access Control (RBAC) Dependency
# -----------------------------------------------------------------------------
security = HTTPBearer(
    auto_error=False,
    description="Bearer JWT access token obtained from /api/v1/auth/login",
)


class CurrentUser(BaseModel):
    """User representation authenticated from JWT token and database."""

    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Development mock tokens for fast local testing (strictly 'admin' and 'user' roles)
MOCK_USERS_BY_TOKEN = {
    "admin-token": CurrentUser(
        id=1,
        username="admin",
        email="admin@huce.edu.vn",
        full_name="HUCE KMS Administrator",
        role="admin",
    ),
    "user-token": CurrentUser(
        id=2,
        username="user",
        email="user@huce.edu.vn",
        full_name="Standard User",
        role="user",
    ),
}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: DatabaseDep,
) -> CurrentUser:
    """Authenticate incoming request using Bearer JWT access token and verify user in database."""
    if not credentials:
        raise UnauthorizedException(
            message="Authentication required: Missing Authorization header.",
        )

    token = credentials.credentials

    # 1. Fallback to development mock tokens only in DEBUG mode
    if settings.DEBUG and token in MOCK_USERS_BY_TOKEN:
        return MOCK_USERS_BY_TOKEN[token]

    # 2. Decode and verify standard JWT access token
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedException(
            message="Invalid or expired access token.",
        )

    # 3. Verify token type is 'access'
    token_type = payload.get("type")
    if token_type and token_type != "access":
        raise UnauthorizedException(
            message="Invalid token type: Expected an access token.",
        )

    username: str = payload["sub"]

    # 4. Query active user from database using UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_username(username)
    if not user:
        raise UnauthorizedException(
            message="User associated with token no longer exists.",
        )

    if not user.is_active:
        raise ForbiddenException(
            message="This account has been deactivated.",
        )

    return CurrentUser(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


def require_role(allowed_roles: list[str]) -> Callable[[CurrentUser], CurrentUser]:
    """Higher-order dependency for Role-Based Access Control (RBAC)."""

    def role_checker(current_user: CurrentUserDep) -> CurrentUser:
        if current_user.role not in allowed_roles:
            roles_str = ", ".join(allowed_roles)
            raise ForbiddenException(
                message=f"Access denied: Endpoint requires role [{roles_str}], but current role is '{current_user.role}'.",
            )
        return current_user

    return role_checker


AdminUserDep = Annotated[CurrentUser, Depends(require_role(["admin"]))]
