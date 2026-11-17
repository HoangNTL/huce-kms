from uuid import UUID
from api.core.exceptions import BadRequestException, ConflictException, EntityNotFoundException
from api.core.security import hash_password
from api.models.user import User
from api.repositories.refresh_token import RefreshTokenRepository
from api.repositories.user import UserRepository
from api.schemas.common import PaginatedData, PaginationMeta
from api.schemas.user import AdminUserCreate, UserResponse, UserUpdate


class UserService:
    """Service handling User administration, querying, and profile updates."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo

    async def create_user_by_admin(self, payload: AdminUserCreate) -> UserResponse:
        """Create a user directly from administrative dashboard with custom role."""
        existing_user = await self.user_repo.get_by_username(payload.username, include_deleted=True)
        if existing_user:
            raise ConflictException(message=f"Username '{payload.username}' is already taken.")

        existing_email = await self.user_repo.get_by_email(payload.email, include_deleted=True)
        if existing_email:
            raise ConflictException(message=f"Email '{payload.email}' is already registered.")

        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            is_active=payload.is_active,
        )
        created_user = await self.user_repo.create(user)
        return UserResponse.model_validate(created_user)

    async def list_users(
        self,
        q: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> PaginatedData[UserResponse]:
        """Fetch paginated users with optional keyword search and filters."""
        users, total = await self.user_repo.search_with_count(
            q=q,
            role=role,
            is_active=is_active,
            skip=skip,
            limit=limit,
        )
        items = [UserResponse.model_validate(user) for user in users]
        pagination = PaginationMeta.create(total=total, skip=skip, limit=limit)
        return PaginatedData(items=items, pagination=pagination)

    async def get_user_by_id(self, user_id: UUID) -> UserResponse:
        """Fetch user by ID."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)
        return UserResponse.model_validate(user)

    async def update_user(self, user_id: UUID, payload: UserUpdate) -> UserResponse:
        """Update basic user profile attributes."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        updated_user = await self.user_repo.update(user)
        return UserResponse.model_validate(updated_user)

    async def update_user_status(self, user_id: UUID, is_active: bool, admin_id: UUID) -> UserResponse:
        """Activate or deactivate a user account (Admin only)."""
        if user_id == admin_id and not is_active:
            raise BadRequestException(message="Admins cannot deactivate their own account.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)

        user.is_active = is_active
        if not is_active:
            # Revoke all active sessions for deactivated user immediately
            await self.refresh_token_repo.revoke_all_for_user(user_id)

        updated_user = await self.user_repo.update(user)
        return UserResponse.model_validate(updated_user)

    async def update_user_role(self, user_id: UUID, role: str, admin_id: UUID) -> UserResponse:
        """Promote or demote user role ('user' or 'admin') (Admin only)."""
        if user_id == admin_id and role != "admin":
            raise BadRequestException(message="Admins cannot revoke their own admin privileges.")

        if role not in ("user", "admin"):
            raise BadRequestException(message="Invalid role. Must be 'user' or 'admin'.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)

        user.role = role
        # Revoke tokens to force re-login with new claims
        await self.refresh_token_repo.revoke_all_for_user(user_id)

        updated_user = await self.user_repo.update(user)
        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: UUID, current_admin_id: UUID) -> None:
        """Soft-delete user account and revoke all active sessions (Admin only)."""
        if user_id == current_admin_id:
            raise BadRequestException(message="Admins cannot delete their own account.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise EntityNotFoundException(entity_name="User", entity_id=user_id)

        user.is_active = False
        await self.refresh_token_repo.revoke_all_for_user(user_id)
        await self.user_repo.soft_delete(user)
        logger.info("Soft-deleted user id=%s ('%s')", user_id, user.username)
