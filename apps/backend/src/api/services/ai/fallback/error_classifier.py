import re
from typing import Any
import httpx

from api.services.ai.schemas.ai import AIErrorType, AIProviderError


def extract_retry_delay(error_str: str) -> float | None:
    """Extract required retry delay in seconds from error payloads if provided by API."""
    match = re.search(r"retryDelay':\s*'([0-9.]+)s'", error_str)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    match = re.search(r"retry in ([0-9.]+)s", error_str, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    match = re.search(r"try again in ([0-9.]+)s", error_str, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


class ErrorClassifier:
    """Standardizes external AI provider exceptions into deterministic AIProviderError instances."""

    @classmethod
    def classify(
        cls,
        provider: str,
        exc: Exception,
        model: str | None = None,
        status_code: int | None = None,
    ) -> AIProviderError:
        """Classify any exception into an AIProviderError with clear AIErrorType."""
        if isinstance(exc, AIProviderError):
            return exc

        err_str = str(exc)
        lower_str = err_str.lower()
        retry_delay = extract_retry_delay(err_str)

        # 1. HTTPX specific status codes
        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            err_str = f"{exc.response.text or err_str}"
            lower_str = err_str.lower()

        # 2. Timeout errors
        if isinstance(exc, (httpx.TimeoutException, TimeoutError)) or "timed out" in lower_str:
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.TIMEOUT,
                message=f"Request to {provider} timed out: {err_str}",
                status_code=408,
                model=model,
                raw_error=exc,
            )

        # 3. Temporary Rate Limiting (RPM/TPM limit with retry delay or per-minute metric)
        is_per_minute = (
            "requests per minute" in lower_str
            or "per-minute" in lower_str
            or "tpm" in lower_str
            or "rpm" in lower_str
        )
        if retry_delay is not None or is_per_minute:
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.RATE_LIMIT_429,
                message=f"{provider} rate limit exceeded: {err_str}",
                status_code=429,
                retry_after=retry_delay or 5.0,
                model=model,
                raw_error=exc,
            )

        # 4. Quota Exhaustion (Permanent for daily limit or billing cycle)
        quota_keywords = [
            "quota_exceeded",
            "insufficient_quota",
            "credit_exhausted",
            "billing",
            "exhausted your quota",
            "exceeded your current quota",
            "free tier quota",
            "daily quota",
            "daily limit",
            "requests per day",
            "balance is not enough",
            "resource has been exhausted",
            "resource_exhausted",
            "check quota",
        ]
        if any(kw in lower_str for kw in quota_keywords):
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.QUOTA_EXHAUSTED,
                message=f"{provider} quota exhausted: {err_str}",
                status_code=status_code or 429,
                retry_after=retry_delay,
                model=model,
                raw_error=exc,
            )

        # 5. General Rate Limiting (429 without explicit delay)
        if (
            status_code == 429
            or "429" in err_str
            or "rate limit" in lower_str
            or "too many requests" in lower_str
        ):
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.RATE_LIMIT_429,
                message=f"{provider} rate limit exceeded: {err_str}",
                status_code=429,
                retry_after=5.0,
                model=model,
                raw_error=exc,
            )

        # 5. Authentication Errors
        if status_code in (401, 403) or "unauthenticated" in lower_str or "api key not valid" in lower_str or "unauthorized" in lower_str:
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.AUTH_ERROR_401,
                message=f"{provider} authentication failed: {err_str}",
                status_code=status_code or 401,
                model=model,
                raw_error=exc,
            )

        # 6. Bad Request / Prompt safety block
        if status_code == 400 or "invalid_argument" in lower_str or "safety" in lower_str or "harmful" in lower_str:
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.INVALID_REQUEST,
                message=f"{provider} bad request / safety block: {err_str}",
                status_code=400,
                model=model,
                raw_error=exc,
            )

        # 7. Server / Gateway Errors (500, 502, 503, 504)
        if (status_code and status_code >= 500) or "503" in err_str or "500" in err_str or "unavailable" in lower_str:
            return AIProviderError(
                provider=provider,
                error_type=AIErrorType.SERVER_ERROR_5XX,
                message=f"{provider} server error: {err_str}",
                status_code=status_code or 503,
                model=model,
                raw_error=exc,
            )

        # 8. Fallback unknown
        return AIProviderError(
            provider=provider,
            error_type=AIErrorType.UNKNOWN,
            message=f"{provider} encountered an unexpected error: {err_str}",
            status_code=status_code,
            model=model,
            raw_error=exc,
        )
