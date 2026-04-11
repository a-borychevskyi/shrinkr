from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import ExceptionHandler
from src.api.v0 import v0_router
from src.di.orm.database import get_db
from src.telemetry import instrument_app, setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = get_db()
    yield
    await app.state.db.stop()


def create_app() -> FastAPI:
    setup_telemetry()

    app = FastAPI(
        title="URL Shortener API",
        version="0.1.0",
        description="A simple URL shortener API",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.include_router(v0_router)
    ExceptionHandler(app).register_handlers()

    instrument_app(app)

    return app
