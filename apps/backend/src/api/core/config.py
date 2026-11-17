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
    AUTO_SEED: bool = True  # Automatically seed default admin and categories on startup in development

    # Qdrant Vector DB Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "huce_kms_documents"

    # AI / LLM & Embedding Configuration (Multi-Provider Support)
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_API_KEY: str | None = None

    GENERATION_PROVIDERS: str | list[str] = ["gemini", "groq", "openrouter"]
    GENERATION_MAX_RETRIES: int = 2
    GENERATION_TIMEOUT: float = 30.0
    PROVIDER_COOLDOWN_SECONDS: int = 900

    # Groq Provider Settings
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # OpenRouter Provider Settings
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "deepseek/deepseek-chat"

    # Embedding Providers Configuration
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"
    VECTOR_DIMENSION: int = 768

    # Voyage AI Provider Settings
    VOYAGE_API_KEY: str | None = None
    VOYAGE_MODEL: str = "voyage-3-lite"

    # Jina AI Provider Settings
    JINA_API_KEY: str | None = None
    JINA_MODEL: str = "jina-embeddings-v3"

    # Document Upload & Ingestion Configuration
    UPLOAD_DIR: Path = BACKEND_DIR / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_DOCUMENT_EXTENSIONS: list[str] = [".pdf", ".txt", ".md"]
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150

    # Object Storage (MinIO / S3 compatible)
    STORAGE_BACKEND: str = "minio"  # "minio" or "local"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "huce-kms-documents"
    MINIO_URL_EXPIRY_SECONDS: int = 3600
    MINIO_PUBLIC_ENDPOINT: str | None = None

    # Crawler Configuration
    CRAWLER_DATA_DIR: Path = BACKEND_DIR / "data" / "crawled"
    CRAWLER_ALLOWED_DOMAINS: list[str] = [
        "huce.edu.vn",
        "drive.google.com",
        "docs.google.com",
        "googleusercontent.com",
    ]
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

    @field_validator("GENERATION_PROVIDERS", mode="before")
    @classmethod
    def parse_generation_providers(cls, value: Any) -> list[str]:
        """Support comma-separated string, JSON array, or list for GENERATION_PROVIDERS in .env."""
        import json

        default_providers = ["gemini", "groq", "openrouter"]
        if value is None:
            return default_providers
        if isinstance(value, str):
            val = value.strip().strip("'\"")
            if not val:
                return default_providers
            if val.startswith("[") and val.endswith("]"):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(p).strip().lower() for p in parsed if str(p).strip()]
                except Exception:
                    pass
            return [p.strip().lower() for p in val.split(",") if p.strip()]
        if isinstance(value, (list, tuple)):
            return [str(p).strip().lower() for p in value if str(p).strip()]
        return default_providers

    @field_validator(
        "GEMINI_API_KEY",
        "QDRANT_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "VOYAGE_API_KEY",
        "JINA_API_KEY",
        mode="before",
    )
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
