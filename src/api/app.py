from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v0 import v0_router
from src.di.orm.database import get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = get_db()
    yield
    app.state.db.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="URL Shortener API",
        version="0.1.0",
        description="A simple URL shortener API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.include_router(v0_router)
    return app
