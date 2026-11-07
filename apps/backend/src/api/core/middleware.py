import logging
import time
import uuid
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api.core.config import settings

logger = logging.getLogger("huce_kms.http")


class RequestLifecycleMiddleware(BaseHTTPMiddleware):
    """Middleware monitoring request lifecycle: adds request ID, timing header and logs HTTP access."""

    # Paths excluded from access logging to prevent noisy health probes from flooding logs
    EXCLUDED_LOG_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. Request start: assign request ID and record start timestamp
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        start_time = time.perf_counter()

        # 2. Forward execution to subsequent handlers
        response = await call_next(request)

        # 3. Request completion: calculate elapsed time in milliseconds
        process_time_ms = (time.perf_counter() - start_time) * 1000

        # 4. Attach standard diagnostic headers to response
        response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
        response.headers["X-Request-ID"] = request_id

        # 5. Emit access log only for business endpoints
        if request.url.path not in self.EXCLUDED_LOG_PATHS:
            logger.info(
                "[%s] %s %s -> Status: %d (%.2fms)",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                process_time_ms,
            )

        return response


def register_middlewares(app: FastAPI) -> None:
    """Register application middleware stack in proper execution order."""

    # 1. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request Lifecycle & Timing Middleware
    app.add_middleware(RequestLifecycleMiddleware)
