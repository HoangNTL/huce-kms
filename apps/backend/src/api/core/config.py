from pathlib import Path
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_DB_PATH = (BACKEND_DIR / "huce_kms.db").as_posix()


class Settings(BaseSettings):
    """Centralized application settings using Pydantic Settings."""

    PROJECT_NAME: str = "HUCE KMS API"
    DESCRIPTION: str = "Knowledge Management System API - Hanoi University of Civil Engineering"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # CORS Configuration
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]

    # Database Configuration (Defaults to absolute path of backend/huce_kms.db)
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"

    # JWT & Security Configuration
    SECRET_KEY: str = "huce-kms-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes for access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days for refresh token

    # Refresh Token Cookie Configuration
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False  # Set to True over HTTPS in production
    COOKIE_SAMESITE: str = "lax"  # CSRF mitigation: "lax", "strict", or "none"
    COOKIE_PATH: str = "/"  # Root path so cookie is stored for the entire origin

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_env(cls, value: Any) -> bool:
        """Prevent collision when system DEBUG environment variable is a string (e.g. 'release')."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes", "on", "debug")
        return bool(value)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
