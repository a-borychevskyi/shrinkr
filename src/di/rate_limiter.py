import time
from typing import Annotated

import structlog
from fastapi import Depends, Request, Response
from opentelemetry import trace
from redis.asyncio import Redis

from src.config.rate_limiter import RateLimiterConfig
from src.di.clients.redis import get_async_redis_client
from src.utils.client_ip import get_client_ip
from src.utils.exceptions.rate_limit import RateLimitExceeded

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

LUA_SCRIPT = """
-- Sliding window counter rate limit.
-- KEYS[1]: current window key
-- KEYS[2]: previous window key
-- ARGV[1]: limit (integer)
-- ARGV[2]: window size in seconds (integer)
-- ARGV[3]: current unix timestamp (integer)
-- Returns: {allowed (0|1), remaining (integer), reset_at (unix timestamp)}

local current_key = KEYS[1]
local previous_key = KEYS[2]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local window_start = now - (now % window)
local elapsed = now - window_start

local prev_count = tonumber(redis.call('GET', previous_key)) or 0
local current_count = tonumber(redis.call('GET', current_key)) or 0

local estimate = prev_count * (1 - elapsed / window) + current_count

if estimate >= limit then
    local reset_at = window_start + window
    return {0, 0, reset_at}
end

local new_val = redis.call('INCR', current_key)
if new_val == 1 then
    redis.call('EXPIRE', current_key, window * 2)
end

local new_count = current_count + 1
local new_estimate = prev_count * (1 - elapsed / window) + new_count
local remaining = math.max(0, math.floor(limit - new_estimate))
local reset_at = window_start + window

return {1, remaining, reset_at}
"""


class RateLimiter:
    """Sliding window rate limiter using Redis as the backing store.

    Implements the sliding window counter algorithm: the previous window's
    request count is weighted by the proportion of the current window that
    has elapsed, giving a smooth rate limit that avoids the boundary spike
    problem of fixed window counters.

    Usage::

        limiter = RateLimiter(times=60, seconds=60)

        @router.post("/links", dependencies=[Depends(limiter)])
        async def create_link(...): ...

    Args:
        times: Maximum number of requests allowed per window. When ``None``
            the value is read from ``RATE_LIMIT_DEFAULT_TIMES`` at init time.
        seconds: Window size in seconds. When ``None`` the value is read from
            ``RATE_LIMIT_DEFAULT_WINDOW`` at init time.
    """

    def __init__(self, times: int | None = None, seconds: int | None = None) -> None:
        config = RateLimiterConfig()
        self._enabled = config.RATE_LIMIT_ENABLED
        self._times = times if times is not None else config.RATE_LIMIT_DEFAULT_TIMES
        self._seconds = (
            seconds if seconds is not None else config.RATE_LIMIT_DEFAULT_WINDOW
        )
        self._key_prefix = f"{config.APP_PREFIX}:{config.RATE_LIMIT_KEY_PREFIX}"

    async def __call__(
        self,
        request: Request,
        response: Response,
        redis: Annotated[Redis, Depends(get_async_redis_client)],
    ) -> None:
        if not self._enabled:
            return

        client_ip = get_client_ip(request)

        route = request.scope.get("route")
        route_pattern: str = route.path if route else request.url.path

        now = int(time.time())
        window_start = now - (now % self._seconds)
        prev_window_start = window_start - self._seconds
        current_key = f"{self._key_prefix}:{client_ip}:{route_pattern}:{window_start}"
        previous_key = (
            f"{self._key_prefix}:{client_ip}:{route_pattern}:{prev_window_start}"
        )

        with tracer.start_as_current_span(
            "rate_limit.check",
            attributes={
                "rate_limit.client_ip": client_ip,
                "rate_limit.route": route_pattern,
                "rate_limit.limit": self._times,
            },
        ) as span:
            result = await redis.eval(
                LUA_SCRIPT,
                2,
                current_key,
                previous_key,
                str(self._times),
                str(self._seconds),
                str(now),
            )

            allowed, remaining, reset_at = (
                int(result[0]),
                int(result[1]),
                int(result[2]),
            )

            span.set_attribute("rate_limit.allowed", bool(allowed))
            span.set_attribute("rate_limit.remaining", remaining)

            response.headers["X-RateLimit-Limit"] = str(self._times)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)

            if not allowed:
                retry_after = max(1, reset_at - now)
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    route=route_pattern,
                    limit=self._times,
                    window_seconds=self._seconds,
                )
                raise RateLimitExceeded(
                    retry_after=retry_after,
                    headers={
                        "X-RateLimit-Limit": str(self._times),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                    },
                )
