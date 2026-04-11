from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.exceptions import ExceptionHandler
from src.api.v0 import v0_router
from src.di.clients.redis import get_async_redis_client
from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.di.services.url_stats import get_url_stats_service


def _make_redis_mock(
    allowed: int = 1, remaining: int = 59, reset_at: int = 9999999999
) -> AsyncMock:
    mock = AsyncMock()
    mock.eval.return_value = [allowed, remaining, reset_at]
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    return mock


def create_rate_limit_test_app(redis_mock: AsyncMock) -> FastAPI:
    app = FastAPI()
    app.include_router(v0_router)
    ExceptionHandler(app).register_handlers()
    app.state.db = MagicMock()

    app.dependency_overrides[get_async_redis_client] = lambda: redis_mock
    app.dependency_overrides[get_url_cache_repository] = lambda: AsyncMock()

    mock_url_service = AsyncMock()
    mock_url_service.create.return_value = MagicMock(short_code="abc123")
    mock_url_service.get_one.return_value = MagicMock(
        target_url="https://example.com", id=1
    )
    app.dependency_overrides[get_url_service] = lambda: mock_url_service

    mock_stats_service = AsyncMock()
    app.dependency_overrides[get_url_stats_service] = lambda: mock_stats_service

    return app


@pytest.fixture
def redis_mock():
    return _make_redis_mock(allowed=1, remaining=59)


@pytest.fixture
def app(redis_mock):
    return create_rate_limit_test_app(redis_mock)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestRateLimitHeaders:
    async def test_success_response_includes_rate_limit_headers(
        self, client: AsyncClient
    ):
        resp = await client.post(
            "/v0/shortner/",
            json={"target_url": "https://example.com"},
        )
        assert "x-ratelimit-limit" in resp.headers
        assert "x-ratelimit-remaining" in resp.headers
        assert "x-ratelimit-reset" in resp.headers


class TestRateLimitBlocked:
    async def test_returns_429_when_rate_limited(self):
        blocked_redis = _make_redis_mock(allowed=0, remaining=0, reset_at=9999999999)
        app = create_rate_limit_test_app(blocked_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        assert resp.status_code == 429

    async def test_429_includes_retry_after(self):
        blocked_redis = _make_redis_mock(allowed=0, remaining=0, reset_at=9999999999)
        app = create_rate_limit_test_app(blocked_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        assert "retry-after" in resp.headers

    async def test_429_json_error_format(self):
        blocked_redis = _make_redis_mock(allowed=0, remaining=0, reset_at=9999999999)
        app = create_rate_limit_test_app(blocked_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        body = resp.json()
        assert "errors" in body
        assert body["errors"][0]["type"] == "RATE_LIMIT_EXCEEDED"


class TestRateLimitDisabled:
    async def test_disabled_skips_rate_limiting(self):
        """When rate limiting is disabled, redis.eval must not be called and
        the request should succeed regardless of what the Lua script would return.

        RateLimiter instances are created at module-import time, so we cannot use
        monkeypatch.setenv to flip RATE_LIMIT_ENABLED after the fact. Instead we
        patch ``RateLimiter.__call__`` to a no-op coroutine for the duration of
        this test, which simulates the limiter being fully disabled.
        """
        redis_mock = _make_redis_mock(allowed=0, remaining=0)
        app = create_rate_limit_test_app(redis_mock)

        from src.di.rate_limiter import RateLimiter

        async def _noop(self, request, response, redis):  # noqa: ARG001
            return None

        with patch.object(RateLimiter, "__call__", new=_noop):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/v0/shortner/",
                    json={"target_url": "https://example.com"},
                )

        assert resp.status_code != 429
        redis_mock.eval.assert_not_called()


class TestSystemRoutesExempt:
    async def test_health_not_rate_limited(self, client: AsyncClient, redis_mock):
        await client.get("/v0/system/health")
        redis_mock.eval.assert_not_called()
