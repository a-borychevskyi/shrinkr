import time
from typing import Annotated

from fastapi import Depends, Request, Response
from loguru import logger
from opentelemetry import trace
from redis.asyncio import Redis

from src.config.rate_limiter import RateLimiterConfig
from src.di.clients.redis import get_async_redis_client
from src.utils.client_ip import get_client_ip
from src.utils.exceptions.rate_limit import RateLimitExceeded

tracer = trace.get_tracer(__name__)

LUA_SCRIPT = """
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

redis.call('INCR', current_key)
redis.call('EXPIRE', current_key, window * 2)

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
            the value is read from ``RATE_LIMIT_DEFAULT_TIMES`` at call time.
        seconds: Window size in seconds. When ``None`` the value is read from
            ``RATE_LIMIT_DEFAULT_WINDOW`` at call time.
    """

    def __init__(self, times: int | None = None, seconds: int | None = None) -> None:
        self._times = times
        self._seconds = seconds

    async def __call__(
        self,
        request: Request,
        response: Response,
        redis: Annotated[Redis, Depends(get_async_redis_client)],
    ) -> None:
        """Apply the rate limit to the current request.

        Sets ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, and
        ``X-RateLimit-Reset`` response headers regardless of outcome.
        Raises ``RateLimitExceeded`` (HTTP 429) when the limit is breached.

        Args:
            request: The incoming FastAPI request.
            response: The outgoing FastAPI response (headers are mutated).
            redis: An async Redis client injected via FastAPI DI.

        Raises:
            RateLimitExceeded: When the sliding-window estimate exceeds the
                configured limit for the client IP + route combination.
        """
        config = RateLimiterConfig()

        if not config.RATE_LIMIT_ENABLED:
            return

        times = (
            self._times if self._times is not None else config.RATE_LIMIT_DEFAULT_TIMES
        )
        seconds = (
            self._seconds
            if self._seconds is not None
            else config.RATE_LIMIT_DEFAULT_WINDOW
        )

        client_ip = get_client_ip(request)

        route = request.scope.get("route")
        route_pattern: str = route.path if route else request.url.path

        now = int(time.time())
        window_start = now - (now % seconds)
        prev_window_start = window_start - seconds

        prefix = f"{config.APP_PREFIX}:{config.RATE_LIMIT_KEY_PREFIX}"
        current_key = f"{prefix}:{client_ip}:{route_pattern}:{window_start}"
        previous_key = f"{prefix}:{client_ip}:{route_pattern}:{prev_window_start}"

        with tracer.start_as_current_span(
            "rate_limit.check",
            attributes={
                "rate_limit.client_ip": client_ip,
                "rate_limit.route": route_pattern,
                "rate_limit.limit": times,
            },
        ) as span:
            result = await redis.eval(
                LUA_SCRIPT,
                2,
                current_key,
                previous_key,
                str(times),
                str(seconds),
                str(now),
            )

            allowed, remaining, reset_at = (
                int(result[0]),
                int(result[1]),
                int(result[2]),
            )

            span.set_attribute("rate_limit.allowed", bool(allowed))
            span.set_attribute("rate_limit.remaining", remaining)

            response.headers["X-RateLimit-Limit"] = str(times)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)

            if not allowed:
                retry_after = max(1, reset_at - now)
                logger.warning(
                    "Rate limit exceeded: ip={} route={} limit={}/{}s",
                    client_ip,
                    route_pattern,
                    times,
                    seconds,
                )
                raise RateLimitExceeded(
                    retry_after=retry_after,
                    headers={
                        "X-RateLimit-Limit": str(times),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                    },
                )
