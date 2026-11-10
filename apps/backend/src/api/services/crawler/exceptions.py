from api.core.exceptions import AppException


class CrawlerException(AppException):
    """Base exception for all crawler domain errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="CRAWLER_ERROR",
            details=details,
        )


class SSRFBlockedException(CrawlerException):
    """Raised when an URL violates security allowlist or targets private IP."""

    def __init__(self, message: str, url: str | None = None):
        super().__init__(
            message=message,
            details={"url": url} if url else None,
        )
        self.error_code = "CRAWLER_SSRF_BLOCKED"


class FetchException(CrawlerException):
    """Raised when fetching an URL fails (network, status >= 400)."""

    def __init__(self, message: str, url: str | None = None, status_code: int | None = None):
        super().__init__(
            message=message,
            details={"url": url, "http_status": status_code},
        )
        self.error_code = "CRAWLER_FETCH_FAILED"


class MediaDownloadException(CrawlerException):
    """Raised when downloading a media attachment fails or exceeds size limit."""

    def __init__(self, message: str, url: str | None = None):
        super().__init__(
            message=message,
            details={"url": url} if url else None,
        )
        self.error_code = "CRAWLER_MEDIA_DOWNLOAD_FAILED"
