from pathlib import Path
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent


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
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # Database Configuration (Docker PostgreSQL by default)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/huce_kms"

    # Qdrant Vector DB Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "huce_kms_documents"

    # AI / LLM & Embedding Configuration (Google Gemini)
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_API_KEY: str | None = None

    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"
    VECTOR_DIMENSION: int = 768

    # Document Upload & Ingestion Configuration
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = [".pdf", ".txt", ".md"]
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150

    # Crawler Configuration
    CRAWLER_DATA_DIR: Path = BACKEND_DIR / "data" / "crawled"
    CRAWLER_ALLOWED_DOMAINS: list[str] = ["huce.edu.vn"]
    CRAWLER_REQUEST_TIMEOUT: int = 15
    CRAWLER_MAX_RETRIES: int = 2
    CRAWLER_MAX_FILE_SIZE_MB: int = 20
    CRAWLER_USER_AGENT: str = "HUCE-KMS-Crawler/1.0 (+https://huce.edu.vn)"

    # JWT & Security Configuration
    SECRET_KEY: str = "huce-kms-super-secret-key-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes access token (OWASP standard)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days refresh token

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

    @field_validator("GEMINI_API_KEY", "QDRANT_API_KEY", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: Any) -> str | None:
        """Sanitize optional API keys: strip quotes/whitespace and treat empty strings as None."""
        if isinstance(value, str):
            val = value.strip().strip("'\"")
            return val or None
        return value

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR.parent.parent / ".env"), str(BACKEND_DIR / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
