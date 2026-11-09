import logging
import logging.handlers
from pathlib import Path

from api.core.config import settings

# Directory for persistent application log files
LOGS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"


def setup_logging() -> None:
    """Configure centralized production-ready logging."""
    # Ensure logs/ directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file_path = LOGS_DIR / "app.log"

    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Standard format: ISO 8601 Timestamp | Level | Logger Name | Message
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # 1. Console Handler (Standard Output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    # 2. Rotating File Handler (Max 10MB per file, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Configure Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear pre-existing handlers to prevent duplicate log records
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress verbose logs from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
