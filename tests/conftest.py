from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.exceptions import ExceptionHandler
from src.api.v0 import v0_router
from src.di.repositories.url import get_url_cache_repository


def create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(v0_router)
    ExceptionHandler(app).register_handlers()
    app.state.db = MagicMock()
    app.dependency_overrides[get_url_cache_repository] = lambda: AsyncMock()
    return app


@pytest.fixture
def app() -> FastAPI:
    return create_test_app()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
