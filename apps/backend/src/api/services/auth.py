from datetime import datetime, timezone
import logging

from api.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from api.core.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
    verify_password,
)
from api.models.refresh_token import RefreshToken
from api.models.user import User
from api.repositories.refresh_token import RefreshTokenRepository
from api.repositories.user import UserRepository
from api.schemas.user import UserCreate, UserLogin, UserResponse

logger = logging.getLogger("huce_kms.auth")


class AuthService:
    """Service handling authentication workflows: Registration, Login, Token Rotation & Logout."""

    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo

    async def register(self, payload: UserCreate) -> UserResponse:
        """Register a new user account with default 'user' role."""
        # 1. Verify username uniqueness
        existing_user = await self.user_repo.get_by_username(payload.username)
        if existing_user:
            raise ConflictException(message=f"Tên đăng nhập '{payload.username}' đã được sử dụng.")

        # 2. Verify email uniqueness
        existing_email = await self.user_repo.get_by_email(payload.email)
        if existing_email:
            raise ConflictException(message=f"Địa chỉ email '{payload.email}' đã được đăng ký.")

        # 3. Hash password with Argon2id and create user with default role 'user'
        user = User(
            username=payload.username,
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
            role="user",
            is_active=True,
        )
        created_user = await self.user_repo.create(user)
        return UserResponse.model_validate(created_user)

    async def login(
        self,
        payload: UserLogin,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[UserResponse, str, str]:
        """Authenticate user, issue access token and persist new refresh token session.

        Returns:
            tuple[UserResponse, str, str]: (user_profile, access_token, refresh_token)
        """
        # 1. Find user by username or email and verify password
        user = await self.user_repo.get_by_username_or_email(payload.username)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException(message="Tên đăng nhập, email hoặc mật khẩu không chính xác.")

        # 2. Check active status
        if not user.is_active:
            raise BadRequestException(message="Tài khoản này đã bị khóa hoặc ngừng hoạt động.")

        # 3. Create short-lived Access Token
        access_token = create_access_token({
            "sub": user.username,
            "id": user.id,
            "role": user.role,
        })

        # 4. Generate and persist long-lived Refresh Token in database
        raw_refresh_token = generate_refresh_token()
        refresh_token_record = RefreshToken(
            token=raw_refresh_token,
            user_id=user.id,
            expires_at=get_refresh_token_expiry(),
            is_revoked=False,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        await self.refresh_token_repo.create(refresh_token_record)

        return UserResponse.model_validate(user), access_token, raw_refresh_token

    async def refresh_tokens(
        self,
        raw_refresh_token: str | None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, str, UserResponse]:
        """Validate existing refresh token, perform rotation, and return new token pair.

        Returns:
            tuple[str, str, UserResponse]: (new_access_token, new_refresh_token, user_profile)
        """
        if not raw_refresh_token:
            raise UnauthorizedException(message="Refresh token is missing.")

        token_record = await self.refresh_token_repo.get_by_token(raw_refresh_token)
        if not token_record:
            raise UnauthorizedException(message="Invalid refresh token.")

        # Token Reuse Detection (Security breach: someone used an already-revoked token!)
        if token_record.is_revoked:
            logger.warning(
                "Revoked refresh token reused for user_id=%d. Invalidating all sessions.",
                token_record.user_id,
            )
            await self.refresh_token_repo.revoke_all_for_user(token_record.user_id)
            raise UnauthorizedException(
                message="Security alert: Token reuse detected. All active sessions have been terminated."
            )

        # Check expiration
        now_utc = datetime.now(timezone.utc)
        expires_at = token_record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now_utc:
            await self.refresh_token_repo.revoke(token_record)
            raise UnauthorizedException(message="Refresh token has expired. Please log in again.")

        # Check user status
        user = await self.user_repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            await self.refresh_token_repo.revoke(token_record)
            raise UnauthorizedException(message="User account is no longer active.")

        # Rotate: Revoke the old refresh token
        await self.refresh_token_repo.revoke(token_record)

        # Generate new Access Token
        new_access_token = create_access_token({
            "sub": user.username,
            "id": user.id,
            "role": user.role,
        })

        # Generate and save new Refresh Token
        new_raw_refresh_token = generate_refresh_token()
        new_record = RefreshToken(
            token=new_raw_refresh_token,
            user_id=user.id,
            expires_at=get_refresh_token_expiry(),
            is_revoked=False,
            user_agent=user_agent[:255] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        await self.refresh_token_repo.create(new_record)

        return new_access_token, new_raw_refresh_token, UserResponse.model_validate(user)

    async def logout(self, raw_refresh_token: str | None) -> None:
        """Revoke the current device refresh token."""
        if not raw_refresh_token:
            return

        token_record = await self.refresh_token_repo.get_by_token(raw_refresh_token)
        if token_record and not token_record.is_revoked:
            await self.refresh_token_repo.revoke(token_record)

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        """Verify current password, hash new password, and invalidate all other refresh sessions."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="User account not found.")

        if not verify_password(current_password, user.hashed_password):
            raise BadRequestException(message="Current password is incorrect.")

        if current_password == new_password:
            raise BadRequestException(message="New password must be different from current password.")

        user.hashed_password = hash_password(new_password)
        await self.user_repo.update(user)

        # Invalidate all existing sessions so old sessions cannot be hijacked
        await self.refresh_token_repo.revoke_all_for_user(user_id)
