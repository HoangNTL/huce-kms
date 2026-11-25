import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("huce_kms.exceptions")


# Base Exception & Concrete Domain Exceptions
class AppException(Exception):
    """Base application exception for all domain and HTTP errors."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_SERVER_ERROR",
        message: str = "An unexpected server error occurred.",
        details: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details


class EntityNotFoundException(AppException):
    """Raised when a requested resource/entity is not found (404 Not Found)."""

    def __init__(
        self,
        entity_name: str = "Resource",
        entity_id: Any = None,
        message: str | None = None,
        details: Any = None,
    ):
        if not message:
            message = (
                f"{entity_name} with ID '{entity_id}' not found."
                if entity_id is not None
                else f"{entity_name} not found."
            )
        default_details = (
            {"entity_name": entity_name, "entity_id": entity_id}
            if entity_id is not None
            else {"entity_name": entity_name}
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ENTITY_NOT_FOUND",
            message=message,
            details=details if details is not None else default_details,
        )


# Backward-compatible alias
NotFoundException = EntityNotFoundException


class BadRequestException(AppException):
    """Raised when client provides invalid request data (400 Bad Request)."""

    def __init__(
        self,
        message: str = "Invalid request payload.",
        details: Any = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BAD_REQUEST",
            message=message,
            details=details,
        )


class UnauthorizedException(AppException):
    """Raised when authentication fails or token is missing/invalid (401 Unauthorized)."""

    def __init__(
        self,
        message: str = "Authentication required or invalid credentials.",
        details: Any = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
            message=message,
            details=details,
        )


class ForbiddenException(AppException):
    """Raised when authenticated user lacks necessary permissions (403 Forbidden)."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        details: Any = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=message,
            details=details,
        )


class ConflictException(AppException):
    """Raised when a resource already exists or conflict occurs (409 Conflict)."""

    def __init__(
        self,
        message: str = "Resource already exists or data conflict occurred.",
        details: Any = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT",
            message=message,
            details=details,
        )


# Standardized Error Response Formatter
def format_error_response(
    status_code: int,
    error_code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Create standardized error JSONResponse matching BaseResponse structure."""
    content = {
        "success": False,
        "code": error_code,
        "message": message,
        "details": details,
        "data": None,
    }
    return JSONResponse(status_code=status_code, content=content, headers=headers)


# Global Exception Handlers
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all application-specific exceptions derived from AppException."""
    req_id = getattr(request.state, "request_id", "-")
    if exc.status_code >= 500:
        logger.error(
            "[%s] Server AppException [%s %s] - Code: %s, Message: %s",
            req_id,
            request.method,
            request.url.path,
            exc.error_code,
            exc.message,
        )
    elif exc.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
        logger.warning(
            "[%s] %s [%s %s] - %s",
            req_id,
            exc.error_code,
            request.method,
            request.url.path,
            exc.message,
        )
    else:
        logger.debug(
            "[%s] AppException [%s %s] - Code: %s, Message: %s",
            req_id,
            request.method,
            request.url.path,
            exc.error_code,
            exc.message,
        )

    return format_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize default FastAPI/Starlette HTTPExceptions to unified format."""
    message = exc.detail if isinstance(exc.detail, str) else "HTTP Exception"
    details = None if isinstance(exc.detail, str) else exc.detail
    headers = getattr(exc, "headers", None)

    return format_error_response(
        status_code=exc.status_code,
        error_code=f"HTTP_{exc.status_code}",
        message=message,
        details=details,
        headers=headers,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize Pydantic 422 RequestValidationErrors to unified format."""
    formatted_errors = []
    for error in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in error.get("loc", []))
        formatted_errors.append({
            "field": field_loc,
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "value_error"),
        })

    req_id = getattr(request.state, "request_id", "-")
    logger.warning(
        "[%s] VALIDATION_ERROR [%s %s] - %s",
        req_id,
        request.method,
        request.url.path,
        "; ".join(f"{e['field']}: {e['message']}" for e in formatted_errors[:5]),
    )
    return format_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed. Please check payload fields.",
        details=formatted_errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch unhandled internal server exceptions (500) and conceal sensitive stacktraces."""
    req_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "[%s] Unhandled Exception on [%s %s]: %s",
        req_id,
        request.method,
        request.url.path,
        exc,
    )
    return format_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred. Please contact administrator.",
        details=None,
    )


# Register Exception Handlers on FastAPI app
def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers onto FastAPI instance."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
