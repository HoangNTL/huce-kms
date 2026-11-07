from fastapi import FastAPI, status
from fastapi.responses import JSONResponse, RedirectResponse

from api.core.config import settings
from api.core.exceptions import register_exception_handlers
from api.core.lifespan import lifespan
from api.core.logging import setup_logging
from api.core.middleware import register_middlewares
from api.v1.routes.router import api_router

# Initialize application logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register middlewares and global exception handlers
register_middlewares(app)
register_exception_handlers(app)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root path to interactive Swagger API documentation."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"], summary="Liveness & health probe")
async def health_check():
    """Health check endpoint used by Docker, Kubernetes, and load balancers."""
    is_healthy = getattr(app.state, "is_healthy", True)
    if not is_healthy:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy"},
        )
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }
