from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.exceptions import ExceptionHandler
from src.api.redirect import router as redirect_router
from src.api.v0 import v0_router
from src.config.rate_limiter import RateLimiterConfig
from src.di.clients.redis import get_async_redis_client
from src.di.rate_limiter import get_rate_limiter_config
from src.di.repositories.url import get_url_cache_repository


def _test_rate_limiter_config() -> RateLimiterConfig:
    # Construct explicitly so tests don't depend on the process environment
    # or a .env file being present (CI runs have neither).
    return RateLimiterConfig(
        REDIS_HOST="test",
        REDIS_PORT=6379,
        REDIS_DB=0,
        APP_PREFIX="shrinkr",
    )


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(v0_router)
    app.include_router(redirect_router)
    ExceptionHandler(app).register_handlers()
    app.state.db = MagicMock()
    app.state.click_producer = MagicMock()
    app.dependency_overrides[get_url_cache_repository] = lambda: AsyncMock()
    app.dependency_overrides[get_async_redis_client] = lambda: AsyncMock()
    app.dependency_overrides[get_rate_limiter_config] = _test_rate_limiter_config
    return app


@pytest.fixture
def app() -> FastAPI:
    return create_test_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
