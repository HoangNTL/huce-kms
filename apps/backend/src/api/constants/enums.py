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


class CrawlSessionStatus(IntEnum):
    """Lifecycle states for batch crawl sessions."""
    PENDING = 0
    IN_PROGRESS = 1
    COMPLETED = 2
    FAILED = 3
    CANCELLED = 4
    INTERRUPTED = 5

    @property
    def label(self) -> str:
        mapping = {
            CrawlSessionStatus.PENDING: "Chờ thực hiện",
            CrawlSessionStatus.IN_PROGRESS: "Đang thu thập",
            CrawlSessionStatus.COMPLETED: "Hoàn thành",
            CrawlSessionStatus.FAILED: "Thất bại",
            CrawlSessionStatus.CANCELLED: "Đã hủy",
            CrawlSessionStatus.INTERRUPTED: "Bị gián đoạn",
        }
        return mapping.get(self, "Không xác định")

    @property
    def name_str(self) -> str:
        mapping = {
            CrawlSessionStatus.PENDING: "pending",
            CrawlSessionStatus.IN_PROGRESS: "in_progress",
            CrawlSessionStatus.COMPLETED: "completed",
            CrawlSessionStatus.FAILED: "failed",
            CrawlSessionStatus.CANCELLED: "cancelled",
            CrawlSessionStatus.INTERRUPTED: "interrupted",
        }
        return mapping.get(self, "unknown")

    @classmethod
    def from_str(cls, val: str | None) -> "CrawlSessionStatus":
        if not val:
            return cls.PENDING
        norm = val.strip().lower()
        mapping = {
            "pending": cls.PENDING,
            "0": cls.PENDING,
            "in_progress": cls.IN_PROGRESS,
            "running": cls.IN_PROGRESS,
            "1": cls.IN_PROGRESS,
            "completed": cls.COMPLETED,
            "2": cls.COMPLETED,
            "failed": cls.FAILED,
            "3": cls.FAILED,
            "cancelled": cls.CANCELLED,
            "canceled": cls.CANCELLED,
            "4": cls.CANCELLED,
            "interrupted": cls.INTERRUPTED,
            "5": cls.INTERRUPTED,
        }
        if norm not in mapping:
            raise ValueError(f"Invalid CrawlSessionStatus '{val}'. Must be one of: {list(mapping.keys())}")
        return mapping[norm]


class CrawlItemStatus(IntEnum):
    """Outcome status for single URL within a crawl session."""
    PENDING = 0
    RUNNING = 1
    SUCCESS = 2
    PARTIAL = 3
    FAILED = 4
    SKIPPED = 5

    @property
    def label(self) -> str:
        mapping = {
            CrawlItemStatus.PENDING: "Chờ xử lý",
            CrawlItemStatus.RUNNING: "Đang thu thập",
            CrawlItemStatus.SUCCESS: "Thành công",
            CrawlItemStatus.PARTIAL: "Thành công một phần",
            CrawlItemStatus.FAILED: "Thất bại",
            CrawlItemStatus.SKIPPED: "Bỏ qua",
        }
        return mapping.get(self, "Không xác định")

    @property
    def name_str(self) -> str:
        mapping = {
            CrawlItemStatus.PENDING: "pending",
            CrawlItemStatus.RUNNING: "running",
            CrawlItemStatus.SUCCESS: "success",
            CrawlItemStatus.PARTIAL: "partial",
            CrawlItemStatus.FAILED: "failed",
            CrawlItemStatus.SKIPPED: "skipped",
        }
        return mapping.get(self, "unknown")

    @classmethod
    def from_str(cls, val: str | None) -> "CrawlItemStatus":
        if not val:
            return cls.PENDING
        norm = val.strip().lower()
        mapping = {
            "pending": cls.PENDING,
            "0": cls.PENDING,
            "running": cls.RUNNING,
            "in_progress": cls.RUNNING,
            "1": cls.RUNNING,
            "success": cls.SUCCESS,
            "2": cls.SUCCESS,
            "partial": cls.PARTIAL,
            "3": cls.PARTIAL,
            "failed": cls.FAILED,
            "4": cls.FAILED,
            "skipped": cls.SKIPPED,
            "5": cls.SKIPPED,
        }
        if norm not in mapping:
            raise ValueError(f"Invalid CrawlItemStatus '{val}'. Must be one of: {list(mapping.keys())}")
        return mapping[norm]
