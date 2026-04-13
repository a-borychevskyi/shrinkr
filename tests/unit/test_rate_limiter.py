import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config.rate_limiter import RateLimiterConfig
from src.di.rate_limiter import RateLimiter
from src.utils.exceptions.rate_limit import RateLimitExceeded


def _make_config(
    *,
    enabled: bool = True,
    default_times: int = 60,
    default_window: int = 60,
    key_prefix: str = "rl",
    app_prefix: str = "shrinkr",
) -> RateLimiterConfig:
    return RateLimiterConfig(
        REDIS_HOST="test",
        REDIS_PORT=6379,
        REDIS_DB=0,
        APP_PREFIX=app_prefix,
        RATE_LIMIT_ENABLED=enabled,
        RATE_LIMIT_DEFAULT_TIMES=default_times,
        RATE_LIMIT_DEFAULT_WINDOW=default_window,
        RATE_LIMIT_KEY_PREFIX=key_prefix,
    )


def _make_request(
    path: str = "/v0/shortner/",
    route_path: str | None = None,
    client_host: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    request = MagicMock()
    request.headers = headers or {}
    request.client.host = client_host
    request.url.path = path

    if route_path:
        route = MagicMock()
        route.path = route_path
        request.scope = {"route": route}
    else:
        request.scope = {}

    return request


def _make_redis(allowed: int = 1, remaining: int = 59, reset_at: int = 0) -> AsyncMock:
    if reset_at == 0:
        reset_at = int(time.time()) + 60
    mock = AsyncMock()
    mock.eval.return_value = [allowed, remaining, reset_at]
    return mock


class TestRateLimiterAllowed:
    async def test_request_allowed_under_limit(self):
        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=9)
        config = _make_config()

        await limiter(request, response, redis, config)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "10")
        response.headers.__setitem__.assert_any_call("X-RateLimit-Remaining", "9")

    async def test_request_rejected_over_limit(self):
        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=0, remaining=0)
        config = _make_config()

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter(request, response, redis, config)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers


class TestRateLimiterDisabled:
    async def test_disabled_allows_all(self):
        limiter = RateLimiter(times=1, seconds=1)
        request = _make_request()
        response = MagicMock()
        redis = AsyncMock()
        config = _make_config(enabled=False)

        await limiter(request, response, redis, config)

        redis.eval.assert_not_called()


class TestRateLimiterDefaults:
    async def test_uses_config_defaults(self):
        limiter = RateLimiter()
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=29)
        config = _make_config(default_times=30, default_window=120)

        await limiter(request, response, redis, config)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "30")

    async def test_override_takes_precedence(self):
        limiter = RateLimiter(times=5, seconds=10)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=4)
        config = _make_config(default_times=30)

        await limiter(request, response, redis, config)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "5")


class TestRateLimiterRedisKey:
    async def test_uses_route_pattern_when_available(self):
        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request(
            path="/v0/shortner/abc123",
            route_path="/v0/shortner/{short_code}",
        )
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=9)
        config = _make_config()

        await limiter(request, response, redis, config)

        call_args = redis.eval.call_args
        keys_passed = call_args[0][2]  # first key (current window)
        assert "/v0/shortner/{short_code}" in keys_passed

    async def test_different_ips_get_different_keys(self):
        limiter = RateLimiter(times=10, seconds=60)
        redis = _make_redis(allowed=1, remaining=9)
        config = _make_config()

        request_a = _make_request(client_host="10.0.0.1")
        request_b = _make_request(client_host="10.0.0.2")

        await limiter(request_a, MagicMock(), redis, config)
        await limiter(request_b, MagicMock(), redis, config)

        call_a = redis.eval.call_args_list[0][0][2]
        call_b = redis.eval.call_args_list[1][0][2]
        assert call_a != call_b
