from enum import IntEnum, StrEnum
from typing import Any


class DocumentStatus(IntEnum):
    """
    Finite State Machine (FSM) states for document ingestion pipeline.
    Stored as SmallInteger in PostgreSQL.
    """
    UPLOADED = 0    # File uploaded to storage, pending queue entry
    PENDING = 1     # Enqueued, waiting for extraction worker
    PROCESSING = 2  # Actively parsing (OCR), cleaning, chunking, or embedding
    INDEXED = 3     # Vector embeddings stored in Qdrant and chunks persisted in DB
    FAILED = 4      # Error encountered during ingestion

    @property
    def label(self) -> str:
        labels = {
            DocumentStatus.UPLOADED: "Đã tải lên",
            DocumentStatus.PENDING: "Chờ xử lý",
            DocumentStatus.PROCESSING: "Đang xử lý",
            DocumentStatus.INDEXED: "Đã lập chỉ mục",
            DocumentStatus.FAILED: "Thất bại",
        }
        return labels.get(self, "Không xác định")

    @property
    def name_str(self) -> str:
        names = {
            DocumentStatus.UPLOADED: "uploaded",
            DocumentStatus.PENDING: "pending",
            DocumentStatus.PROCESSING: "processing",
            DocumentStatus.INDEXED: "indexed",
            DocumentStatus.FAILED: "failed",
        }
        return names.get(self, "unknown")

    @classmethod
    def from_str(cls, val: str | None) -> "DocumentStatus":
        if val is None:
            return cls.UPLOADED
        norm = val.strip().lower()
        mapping = {
            "uploaded": cls.UPLOADED,
            "pending": cls.PENDING,
            "processing": cls.PROCESSING,
            "indexed": cls.INDEXED,
            "failed": cls.FAILED,
            "0": cls.UPLOADED,
            "1": cls.PENDING,
            "2": cls.PROCESSING,
            "3": cls.INDEXED,
            "4": cls.FAILED,
        }
        if norm not in mapping:
            raise ValueError(f"Invalid DocumentStatus '{val}'. Must be one of: {list(mapping.keys())}")
        return mapping[norm]


class DocumentSourceType(IntEnum):
    """Document origin: direct upload vs crawled web article."""
    UPLOAD = 1
    CRAWLER = 2

    @property
    def label(self) -> str:
        return "Tải lên trực tiếp" if self == DocumentSourceType.UPLOAD else "Thu thập tự động (Crawler)"

    @property
    def name_str(self) -> str:
        return "upload" if self == DocumentSourceType.UPLOAD else "crawler"

    @classmethod
    def from_str(cls, val: str | None) -> "DocumentSourceType":
        if not val:
            return cls.UPLOAD
        norm = val.strip().lower()
        mapping = {
            "upload": cls.UPLOAD,
            "1": cls.UPLOAD,
            "crawler": cls.CRAWLER,
            "2": cls.CRAWLER,
        }
        if norm not in mapping:
            raise ValueError(f"Invalid DocumentSourceType '{val}'. Must be one of: {list(mapping.keys())}")
        return mapping[norm]


class UserRole(IntEnum):
    """Role-based access control for system users."""
    USER = 1   # Regular student / faculty member
    ADMIN = 2  # System administrator

    @property
    def label(self) -> str:
        return "Quản trị viên" if self == UserRole.ADMIN else "Người dùng"

    @property
    def name_str(self) -> str:
        return "admin" if self == UserRole.ADMIN else "user"

    @classmethod
    def from_str(cls, val: str | None) -> "UserRole":
        if val is None:
            return cls.USER
        norm = val.strip().lower()
        mapping = {
            "user": cls.USER,
            "admin": cls.ADMIN,
            "1": cls.USER,
            "2": cls.ADMIN,
        }
        if norm not in mapping:
            raise ValueError(f"Invalid UserRole '{val}'. Must be one of: {list(mapping.keys())}")
        return mapping[norm]


class ChunkStrategy(StrEnum):
    """Document text splitting algorithms."""
    LEGAL_STRUCTURAL = "legal_structural"
    RECURSIVE = "recursive"


class StorageBackend(StrEnum):
    """Underlying raw object storage backend."""
    MINIO = "minio"
    LOCAL = "local"


class LLMProvider(StrEnum):
    """Text generation LLM service providers."""
    GEMINI = "gemini"
    GROQ = "groq"
    OPENROUTER = "openrouter"


class EmbeddingProvider(StrEnum):
    """Vector embedding service providers."""
    GEMINI = "gemini"
    VOYAGE = "voyage"
    JINA = "jina"


class CrawlerMediaType(StrEnum):
    """Discovered media types during web crawling."""
    PDF = "pdf"
    IMAGE = "image"


class PageCrawlStatus(IntEnum):
    """Web crawler single-page execution outcome."""
    PARTIAL = 0
    SUCCESS = 1
    FAILED = 2

    @property
    def name_str(self) -> str:
        mapping = {
            PageCrawlStatus.PARTIAL: "partial",
            PageCrawlStatus.SUCCESS: "success",
            PageCrawlStatus.FAILED: "failed",
        }
        return mapping.get(self, "failed")


class ReviewQueueStatus(IntEnum):
    """Approval status for discovered candidate URLs."""
    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    CRAWLED = 3

    @property
    def name_str(self) -> str:
        mapping = {
            ReviewQueueStatus.PENDING: "pending",
            ReviewQueueStatus.APPROVED: "approved",
            ReviewQueueStatus.REJECTED: "rejected",
            ReviewQueueStatus.CRAWLED: "crawled",
        }
        return mapping.get(self, "pending")
