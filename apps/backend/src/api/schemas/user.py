from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field


UserRole = Literal["user", "admin"]


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["hoang_kms"])
    email: EmailStr = Field(..., examples=["hoang@huce.edu.vn"])
    full_name: str | None = Field(None, max_length=100, examples=["Hoang Nguyen"])


class UserCreate(UserBase):
    """Payload for public registration. Role is locked to 'user' by default."""

    password: str = Field(..., min_length=6, max_length=100, description="Password minimum 6 characters")


class AdminUserCreate(UserBase):
    """Payload for Admin directly provisioning a user account."""

    password: str = Field(..., min_length=6, max_length=100, description="Password minimum 6 characters")
    role: UserRole = Field(default="user", description="Account role: 'user' or 'admin'")
    is_active: bool = Field(default=True, description="Initial active status")


class ChangePasswordRequest(BaseModel):
    """Payload for changing account password."""

    current_password: str = Field(..., description="Existing account password")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password minimum 6 characters")


class UserLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=100, examples=["Hoang Nguyen Updated"])


class UserStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Active status of the user account")


class UserRoleUpdate(BaseModel):
    role: UserRole = Field(..., description="Account role: 'user' or 'admin'")


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Short-lived Bearer JWT access token")
    token_type: str = "bearer"
    refresh_token: str | None = Field(default=None, description="Refresh token string (also set in secure HTTP-only cookie)")
    user: UserResponse
