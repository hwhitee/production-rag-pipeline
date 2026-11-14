from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1.endpoints import router
from src.core.config import settings
from src.core.logging import setup_logging
from src.db.session import engine

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Enterprise RAG API",
    description="Tenant-isolated document ingestion and retrieval-augmented chat.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.app_env.lower() == "production" else "/docs",
    redoc_url=None if settings.app_env.lower() == "production" else "/redoc",
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
app.include_router(router, prefix="/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def ready() -> dict[str, str]:
    from sqlalchemy import text

    from src.db.session import SessionLocal

    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready"}
