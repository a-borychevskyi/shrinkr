from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.exceptions import ExceptionHandler
from src.api.redirect import router as redirect_router
from src.api.v0 import v0_router
from src.di.orm.database import get_db
from src.di.rate_limiter import get_rate_limiter_config
from src.logging import setup_logging
from src.services.click_ingest import ClickIngester
from src.telemetry import instrument_app, setup_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Touch the rate-limiter config on startup so missing/invalid env vars
    # raise immediately instead of surfacing on the first rate-limited request.
    get_rate_limiter_config()
    app.state.db = get_db()
    app.state.click_ingester = ClickIngester(engine=app.state.db.async_engine)
    await app.state.click_ingester.start()
    yield
    await app.state.click_ingester.stop()
    await app.state.db.stop()


def create_app() -> FastAPI:
    setup_logging()
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
    app.include_router(redirect_router)
    ExceptionHandler(app).register_handlers()

    instrument_app(app)

    return app
