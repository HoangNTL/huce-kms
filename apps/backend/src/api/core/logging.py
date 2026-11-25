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

    app_log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Standard format: ISO 8601 Timestamp | Level | Logger Name | Message
    log_format = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)

    # 1. Console Handler (Standard Output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(app_log_level)
    console_handler.setFormatter(formatter)

    # Keep root at INFO so third-party packages do not flood DEBUG output; scope DEBUG to huce_kms.*
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    logging.getLogger("huce_kms").setLevel(app_log_level)

    # 2. Rotating File Handler (Max 10MB per file, keep 5 backups)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except (PermissionError, OSError):
        # Fallback to console handler if file is locked by another process on Windows
        pass

    # Control SQL query verbosity & suppress noisy third-party transport logs
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.SQL_ECHO else logging.WARNING
    )
    for noisy_logger in (
        "uvicorn.access",
        "asyncpg",
        "urllib3",
        "httpx",
        "httpx2",
        "httpcore",
        "google_genai",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
