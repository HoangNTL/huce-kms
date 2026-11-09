from fastapi import APIRouter

from api.v1.routes import auth, categories, documents, rag, users

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Categories"],
)

api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)

api_router.include_router(
    rag.router,
    prefix="/rag",
    tags=["RAG & Search"],
)
