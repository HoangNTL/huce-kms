from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, Request, Response, status

from api.core.config import settings
from api.core.dependencies import CurrentUserDep, DatabaseDep
from api.repositories.refresh_token import RefreshTokenRepository
from api.repositories.user import UserRepository
from api.schemas.common import BaseResponse
from api.schemas.user import ChangePasswordRequest, TokenResponse, UserCreate, UserLogin, UserResponse
from api.services.auth import AuthService

router = APIRouter()


# -----------------------------------------------------------------------------
# Dependency Factory & Cookie Helpers
# -----------------------------------------------------------------------------
def get_auth_service(db: DatabaseDep) -> AuthService:
    user_repo = UserRepository(db)
    refresh_token_repo = RefreshTokenRepository(db)
    return AuthService(user_repo, refresh_token_repo)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    """Attach secure HTTP-only refresh token cookie to HTTP response."""
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH,
    )


def clear_refresh_token_cookie(response: Response) -> None:
    """Clear refresh token cookie upon logout."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.COOKIE_PATH,
    )


# -----------------------------------------------------------------------------
# Authentication Endpoints
# -----------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account (Role 'user')",
)
async def register(payload: UserCreate, service: AuthServiceDep):
    user = await service.register(payload)
    return BaseResponse(
        code="USER_REGISTERED",
        message="Account registered successfully.",
        data=user,
    )


@router.post(
    "/login",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Login: Returns Bearer access token & sets HTTP-only refresh token cookie",
    responses={
        200: {
            "description": "Login successful. Returns access token and sets secure HTTP-only 'refresh_token' cookie.",
            "headers": {
                "Set-Cookie": {
                    "description": "HTTP-only cookie containing refresh token: refresh_token=<token>; HttpOnly; Path=/; SameSite=lax; Max-Age=604800",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    service: AuthServiceDep,
):
    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    user, access_token, refresh_token = await service.login(
        payload=payload,
        user_agent=user_agent,
        ip_address=client_ip,
    )

    # 1. Set secure HTTP-only cookie on the response
    set_refresh_token_cookie(response, refresh_token)

    # 2. Return payload with access token and refresh token
    return BaseResponse(
        code="LOGIN_SUCCESS",
        message="Logged in successfully.",
        data=TokenResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=refresh_token,
            user=user,
        ),
    )


@router.post(
    "/refresh",
    response_model=BaseResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh token: Rotates refresh token & issues new access token",
    responses={
        200: {
            "description": "Token refreshed successfully. Rotates HTTP-only cookie with new refresh token.",
            "headers": {
                "Set-Cookie": {
                    "description": "Rotated HTTP-only refresh token cookie: refresh_token=<new_token>; HttpOnly; Path=/; SameSite=lax; Max-Age=604800",
                    "schema": {"type": "string"},
                }
            },
        }
    },
)
async def refresh_token(
    request: Request,
    response: Response,
    service: AuthServiceDep,
    raw_refresh_token: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
):
    # Allow cookie extraction from either Cookie dependency or fallback request header/body
    token_to_verify = raw_refresh_token or request.cookies.get(settings.REFRESH_COOKIE_NAME)

    user_agent = request.headers.get("user-agent")
    client_ip = request.client.host if request.client else None

    new_access_token, new_refresh_token, user = await service.refresh_tokens(
        raw_refresh_token=token_to_verify,
        user_agent=user_agent,
        ip_address=client_ip,
    )

    # Rotate HTTP-only cookie with the new refresh token
    set_refresh_token_cookie(response, new_refresh_token)

    return BaseResponse(
        code="TOKEN_REFRESHED",
        message="Token refreshed successfully.",
        data=TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
            user=user,
        ),
    )


@router.post(
    "/logout",
    response_model=BaseResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Logout: Revokes refresh token in database & clears HTTP-only cookie",
)
async def logout(
    response: Response,
    service: AuthServiceDep,
    raw_refresh_token: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
):
    await service.logout(raw_refresh_token)
    clear_refresh_token_cookie(response)

    return BaseResponse(
        code="LOGGED_OUT",
        message="Logged out successfully.",
        data=None,
    )


@router.get(
    "/me",
    response_model=BaseResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve profile of currently authenticated user",
)
async def get_me(current_user: CurrentUserDep):
    return BaseResponse(
        message="User profile retrieved successfully.",
        data=current_user,
    )


@router.post(
    "/change-password",
    response_model=BaseResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Change account password (requires current password)",
)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUserDep,
    response: Response,
    service: AuthServiceDep,
):
    await service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    # Invalidate current session cookie
    clear_refresh_token_cookie(response)

    return BaseResponse(
        code="PASSWORD_CHANGED",
        message="Password updated successfully. Please log in again with your new credentials.",
        data=None,
    )
