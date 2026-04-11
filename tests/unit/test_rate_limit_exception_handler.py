import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.exceptions import ExceptionHandler
from src.utils.exceptions.rate_limit import RateLimitExceeded


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    ExceptionHandler(app).register_handlers()

    @app.get("/rate-limited")
    async def rate_limited_endpoint():
        raise RateLimitExceeded(
            retry_after=30,
            headers={
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890",
            },
        )

    return app


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRateLimitExceptionHandler:
    async def test_returns_429(self, client: AsyncClient):
        resp = await client.get("/rate-limited")
        assert resp.status_code == 429

    async def test_includes_retry_after_header(self, client: AsyncClient):
        resp = await client.get("/rate-limited")
        assert resp.headers["retry-after"] == "30"

    async def test_includes_rate_limit_headers(self, client: AsyncClient):
        resp = await client.get("/rate-limited")
        assert resp.headers["x-ratelimit-limit"] == "10"
        assert resp.headers["x-ratelimit-remaining"] == "0"
        assert resp.headers["x-ratelimit-reset"] == "1234567890"

    async def test_json_error_format(self, client: AsyncClient):
        resp = await client.get("/rate-limited")
        body = resp.json()
        assert "errors" in body
        assert body["errors"][0]["type"] == "RATE_LIMIT_EXCEEDED"
        assert body["errors"][0]["errorMessage"] == "Rate limit exceeded"
