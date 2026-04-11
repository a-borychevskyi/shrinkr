# Rate Limiter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Redis-based sliding window counter rate limiter applied globally with per-route limits, configurable via env vars with per-endpoint overrides.

**Architecture:** A `RateLimiter` callable class used via FastAPI's `Depends()`. Applied at router level on API routers (system routes exempt). Uses an atomic Lua script in Redis to check-and-increment, with proxy-aware IP extraction and composite keys (`ip:route`).

**Tech Stack:** FastAPI, redis.asyncio, pydantic-settings, OpenTelemetry, loguru

**Spec:** `docs/superpowers/specs/2026-04-11-rate-limiter-design.md`

---

## File Structure

| File | Responsibility |
|---|---|
| `src/config/rate_limiter.py` | `RateLimiterConfig` — env-driven defaults |
| `src/utils/client_ip.py` | `get_client_ip()` — proxy-aware IP extraction |
| `src/utils/exceptions/rate_limit.py` | `RateLimitExceeded` exception with headers |
| `src/di/rate_limiter.py` | `RateLimiter` callable class + Lua script |
| `src/api/exceptions.py` | Add `RateLimitExceeded` handler (modify) |
| `src/api/v0/__init__.py` | Wire rate limiter to API routers (modify) |
| `tests/unit/test_client_ip.py` | Unit tests for IP extraction |
| `tests/unit/test_rate_limiter.py` | Unit tests for RateLimiter logic |
| `tests/api/test_rate_limiter.py` | API-level tests for 429, headers |

---

### Task 1: RateLimiterConfig

**Files:**
- Create: `src/config/rate_limiter.py`
- Test: `tests/unit/test_rate_limiter_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rate_limiter_config.py
from src.config.rate_limiter import RateLimiterConfig


class TestRateLimiterConfig:
    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        config = RateLimiterConfig()

        assert config.RATE_LIMIT_DEFAULT_TIMES == 60
        assert config.RATE_LIMIT_DEFAULT_WINDOW == 60
        assert config.RATE_LIMIT_ENABLED is True
        assert config.RATE_LIMIT_KEY_PREFIX == "rl"

    def test_override_via_env(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_TIMES", "100")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_WINDOW", "120")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_KEY_PREFIX", "ratelimit")

        config = RateLimiterConfig()

        assert config.RATE_LIMIT_DEFAULT_TIMES == 100
        assert config.RATE_LIMIT_DEFAULT_WINDOW == 120
        assert config.RATE_LIMIT_ENABLED is False
        assert config.RATE_LIMIT_KEY_PREFIX == "ratelimit"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rate_limiter_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config.rate_limiter'`

- [ ] **Step 3: Write the implementation**

```python
# src/config/rate_limiter.py
from typing import Annotated

from pydantic import Field

from src.config.redis import RedisConfig


class RateLimiterConfig(RedisConfig):
    RATE_LIMIT_DEFAULT_TIMES: Annotated[
        int, Field(default=60, description="Default max requests per window")
    ]
    RATE_LIMIT_DEFAULT_WINDOW: Annotated[
        int, Field(default=60, description="Default window size in seconds")
    ]
    RATE_LIMIT_ENABLED: Annotated[
        bool, Field(default=True, description="Global kill switch for rate limiting")
    ]
    RATE_LIMIT_KEY_PREFIX: Annotated[
        str, Field(default="rl", description="Redis key namespace for rate limiting")
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_rate_limiter_config.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/config/rate_limiter.py tests/unit/test_rate_limiter_config.py
git commit -m "feat: add RateLimiterConfig with env-driven defaults"
```

---

### Task 2: Client IP Extraction

**Files:**
- Create: `src/utils/client_ip.py`
- Create: `tests/unit/test_client_ip.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_client_ip.py
from unittest.mock import MagicMock

from src.utils.client_ip import get_client_ip


def _make_request(
    headers: dict[str, str] | None = None,
    client_host: str | None = "127.0.0.1",
) -> MagicMock:
    request = MagicMock()
    request.headers = headers or {}
    if client_host:
        request.client.host = client_host
    else:
        request.client = None
    return request


class TestGetClientIp:
    def test_x_forwarded_for_single(self):
        request = _make_request(headers={"x-forwarded-for": "203.0.113.1"})
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_multiple_takes_first(self):
        request = _make_request(
            headers={"x-forwarded-for": "203.0.113.1, 10.0.0.1, 10.0.0.2"}
        )
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_with_whitespace(self):
        request = _make_request(headers={"x-forwarded-for": "  203.0.113.1  "})
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_when_no_forwarded_for(self):
        request = _make_request(headers={"x-real-ip": "203.0.113.2"})
        assert get_client_ip(request) == "203.0.113.2"

    def test_x_forwarded_for_takes_priority_over_x_real_ip(self):
        request = _make_request(
            headers={
                "x-forwarded-for": "203.0.113.1",
                "x-real-ip": "203.0.113.2",
            }
        )
        assert get_client_ip(request) == "203.0.113.1"

    def test_falls_back_to_client_host(self):
        request = _make_request(headers={}, client_host="192.168.1.1")
        assert get_client_ip(request) == "192.168.1.1"

    def test_no_client_returns_unknown(self):
        request = _make_request(headers={}, client_host=None)
        assert get_client_ip(request) == "unknown"

    def test_empty_x_forwarded_for_falls_back(self):
        request = _make_request(
            headers={"x-forwarded-for": ""},
            client_host="192.168.1.1",
        )
        assert get_client_ip(request) == "192.168.1.1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_client_ip.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.utils.client_ip'`

- [ ] **Step 3: Write the implementation**

```python
# src/utils/client_ip.py
from fastapi import Request


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    real_ip = request.headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_client_ip.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/utils/client_ip.py tests/unit/test_client_ip.py
git commit -m "feat: add proxy-aware client IP extraction utility"
```

---

### Task 3: RateLimitExceeded Exception

**Files:**
- Create: `src/utils/exceptions/rate_limit.py`
- Modify: `src/api/exceptions.py` (add dedicated handler)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rate_limit_exception.py
from src.utils.exceptions.rate_limit import RateLimitExceeded


class TestRateLimitExceeded:
    def test_status_code(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.status_code == 429

    def test_literal(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.literal == "RATE_LIMIT_EXCEEDED"

    def test_default_message(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.message == "Rate limit exceeded"

    def test_custom_message(self):
        exc = RateLimitExceeded(retry_after=30, message="Too many requests")
        assert exc.message == "Too many requests"

    def test_retry_after(self):
        exc = RateLimitExceeded(retry_after=45)
        assert exc.retry_after == 45

    def test_headers(self):
        exc = RateLimitExceeded(
            retry_after=30,
            headers={
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890",
            },
        )
        assert exc.headers["X-RateLimit-Limit"] == "10"
        assert exc.headers["Retry-After"] == "30"

    def test_to_error_response(self):
        exc = RateLimitExceeded(retry_after=30)
        resp = exc.to_error_response()
        assert len(resp.errors) == 1
        assert resp.errors[0].type == "RATE_LIMIT_EXCEEDED"

    def test_not_reported_to_sentry(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.report_to_sentry is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rate_limit_exception.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the implementation**

```python
# src/utils/exceptions/rate_limit.py
from src.utils.exceptions.base import BaseApplicationException


class RateLimitExceeded(BaseApplicationException):
    literal = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    report_to_sentry = False

    def __init__(
        self,
        retry_after: int,
        message: str = "Rate limit exceeded",
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.headers = headers or {}
        self.headers["Retry-After"] = str(retry_after)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_rate_limit_exception.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/utils/exceptions/rate_limit.py tests/unit/test_rate_limit_exception.py
git commit -m "feat: add RateLimitExceeded exception with retry-after headers"
```

---

### Task 4: Add RateLimitExceeded Exception Handler

**Files:**
- Modify: `src/api/exceptions.py` (add handler for `RateLimitExceeded`)

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_rate_limit_exception_handler.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_rate_limit_exception_handler.py -v`
Expected: FAIL — headers not present (base handler doesn't include them)

- [ ] **Step 3: Add the handler to ExceptionHandler**

In `src/api/exceptions.py`, add this import at the top:

```python
from src.utils.exceptions.rate_limit import RateLimitExceeded
```

Inside `register_handlers()`, add this handler **before** the `BaseApplicationException` handler:

```python
@self.app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(
    request: Request, exc: RateLimitExceeded
) -> JSONResponse:
    logger.warning(f"Rate limit exceeded: {exc}")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_response_to_dict(exc.to_error_response()),
        headers=exc.headers,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_rate_limit_exception_handler.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run existing tests to check for regressions**

Run: `pytest tests/ -v`
Expected: All existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add src/api/exceptions.py tests/unit/test_rate_limit_exception_handler.py
git commit -m "feat: add exception handler for RateLimitExceeded with headers"
```

---

### Task 5: RateLimiter Dependency

**Files:**
- Create: `src/di/rate_limiter.py`
- Create: `tests/unit/test_rate_limiter.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/test_rate_limiter.py
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.di.rate_limiter import RateLimiter
from src.utils.exceptions.rate_limit import RateLimitExceeded


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
    async def test_request_allowed_under_limit(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=9)

        await limiter(request, response, redis)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "10")
        response.headers.__setitem__.assert_any_call("X-RateLimit-Remaining", "9")

    async def test_request_rejected_over_limit(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=0, remaining=0)

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter(request, response, redis)

        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers


class TestRateLimiterDisabled:
    async def test_disabled_allows_all(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        limiter = RateLimiter(times=1, seconds=1)
        request = _make_request()
        response = MagicMock()
        redis = AsyncMock()

        await limiter(request, response, redis)

        redis.eval.assert_not_called()


class TestRateLimiterDefaults:
    async def test_uses_config_defaults(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_TIMES", "30")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_WINDOW", "120")

        limiter = RateLimiter()
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=29)

        await limiter(request, response, redis)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "30")

    async def test_override_takes_precedence(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_TIMES", "30")

        limiter = RateLimiter(times=5, seconds=10)
        request = _make_request()
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=4)

        await limiter(request, response, redis)

        response.headers.__setitem__.assert_any_call("X-RateLimit-Limit", "5")


class TestRateLimiterRedisKey:
    async def test_uses_route_pattern_when_available(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        limiter = RateLimiter(times=10, seconds=60)
        request = _make_request(
            path="/v0/shortner/abc123",
            route_path="/v0/shortner/{short_code}",
        )
        response = MagicMock()
        redis = _make_redis(allowed=1, remaining=9)

        await limiter(request, response, redis)

        call_args = redis.eval.call_args
        keys_passed = call_args[0][2]  # first key (current window)
        assert "/v0/shortner/{short_code}" in keys_passed

    async def test_different_ips_get_different_keys(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        limiter = RateLimiter(times=10, seconds=60)
        redis = _make_redis(allowed=1, remaining=9)

        request_a = _make_request(client_host="10.0.0.1")
        request_b = _make_request(client_host="10.0.0.2")

        await limiter(request_a, MagicMock(), redis)
        await limiter(request_b, MagicMock(), redis)

        call_a = redis.eval.call_args_list[0][0][2]
        call_b = redis.eval.call_args_list[1][0][2]
        assert call_a != call_b
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_rate_limiter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.di.rate_limiter'`

- [ ] **Step 3: Write the implementation**

```python
# src/di/rate_limiter.py
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
    def __init__(self, times: int | None = None, seconds: int | None = None):
        self._times = times
        self._seconds = seconds

    async def __call__(
        self,
        request: Request,
        response: Response,
        redis: Annotated[Redis, Depends(get_async_redis_client)],
    ) -> None:
        config = RateLimiterConfig()

        if not config.RATE_LIMIT_ENABLED:
            return

        times = self._times if self._times is not None else config.RATE_LIMIT_DEFAULT_TIMES
        seconds = self._seconds if self._seconds is not None else config.RATE_LIMIT_DEFAULT_WINDOW

        client_ip = get_client_ip(request)

        route = request.scope.get("route")
        route_pattern = route.path if route else request.url.path

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
                LUA_SCRIPT, 2, current_key, previous_key,
                str(times), str(seconds), str(now),
            )

            allowed, remaining, reset_at = int(result[0]), int(result[1]), int(result[2])

            span.set_attribute("rate_limit.allowed", bool(allowed))
            span.set_attribute("rate_limit.remaining", remaining)

            response.headers["X-RateLimit-Limit"] = str(times)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_at)

            if not allowed:
                retry_after = max(1, reset_at - now)
                logger.warning(
                    f"Rate limit exceeded: ip={client_ip} route={route_pattern} "
                    f"limit={times}/{seconds}s"
                )
                raise RateLimitExceeded(
                    retry_after=retry_after,
                    headers={
                        "X-RateLimit-Limit": str(times),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_at),
                    },
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_rate_limiter.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/di/rate_limiter.py tests/unit/test_rate_limiter.py
git commit -m "feat: add RateLimiter dependency with sliding window counter"
```

---

### Task 6: Wire Rate Limiter to Routers

**Files:**
- Modify: `src/api/v0/__init__.py`

- [ ] **Step 1: Modify v0 router to apply rate limiter to API routers**

In `src/api/v0/__init__.py`, change from:

```python
from fastapi import APIRouter

from src.api.v0.shortener.url.endpoints import router as shortner_url_router
from src.api.v0.shortener.url_stats.endpoints import router as shortner_url_stats_router
from src.api.v0.system.endpoints import router as system_router

v0_router = APIRouter(prefix="/v0")
v0_router.include_router(system_router)
v0_router.include_router(shortner_url_router)
v0_router.include_router(shortner_url_stats_router)
```

To:

```python
from fastapi import APIRouter, Depends

from src.api.v0.shortener.url.endpoints import router as shortner_url_router
from src.api.v0.shortener.url_stats.endpoints import router as shortner_url_stats_router
from src.api.v0.system.endpoints import router as system_router
from src.di.rate_limiter import RateLimiter

v0_router = APIRouter(prefix="/v0")
v0_router.include_router(system_router)
v0_router.include_router(
    shortner_url_router, dependencies=[Depends(RateLimiter())]
)
v0_router.include_router(
    shortner_url_stats_router, dependencies=[Depends(RateLimiter())]
)
```

- [ ] **Step 2: Run existing tests to check for regressions**

Run: `pytest tests/ -v`
Expected: All existing tests pass (rate limiter uses Redis via Depends, which tests already override)

Note: If existing tests fail because `RateLimiter` tries to connect to Redis, the test `conftest.py` needs a rate limiter override. In that case, add to `tests/conftest.py`:

```python
from src.di.rate_limiter import RateLimiter

# Add inside create_test_app():
async def noop_rate_limiter():
    pass

app.dependency_overrides[RateLimiter().__call__] = noop_rate_limiter
```

However, since `RateLimiter()` creates a new instance each time, the override won't match by identity. The correct approach is to extract the dependency into a factory function. If this is needed, create a helper:

In `src/di/rate_limiter.py`, add at module level after the `RateLimiter` class:

```python
_default_rate_limiter = RateLimiter()

def get_rate_limiter():
    return _default_rate_limiter
```

And in `src/api/v0/__init__.py`, use the instance directly via `dependencies=[Depends(RateLimiter())]` — FastAPI resolves the `Depends` on the `__call__` method's sub-dependencies (like `redis`), which CAN be overridden via `dependency_overrides[get_async_redis_client]`. Since tests already override `get_url_cache_repository` (which also depends on `get_async_redis_client`), the rate limiter's Redis dependency should resolve to a mock.

If the rate limiter's `RateLimiterConfig()` fails due to missing env vars in tests, add to the test fixtures:

```python
@pytest.fixture(autouse=True)
def rate_limiter_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
```

- [ ] **Step 3: Commit**

```bash
git add src/api/v0/__init__.py
git commit -m "feat: wire RateLimiter to API routers, system routes exempt"
```

---

### Task 7: API-Level Tests

**Files:**
- Create: `tests/api/test_rate_limiter.py`

- [ ] **Step 1: Write the API tests**

```python
# tests/api/test_rate_limiter.py
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.exceptions import ExceptionHandler
from src.api.v0 import v0_router
from src.di.clients.redis import get_async_redis_client
from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.di.services.url_stats import get_url_stats_service


def _make_redis_mock(allowed: int = 1, remaining: int = 59, reset_at: int = 9999999999) -> AsyncMock:
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
def app(redis_mock, monkeypatch):
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("APP_PREFIX", "shrinkr")
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
    async def test_returns_429_when_rate_limited(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        blocked_redis = _make_redis_mock(allowed=0, remaining=0, reset_at=9999999999)
        app = create_rate_limit_test_app(blocked_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        assert resp.status_code == 429

    async def test_429_includes_retry_after(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        blocked_redis = _make_redis_mock(allowed=0, remaining=0, reset_at=9999999999)
        app = create_rate_limit_test_app(blocked_redis)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        assert "retry-after" in resp.headers

    async def test_429_json_error_format(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

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
    async def test_disabled_skips_rate_limiting(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")

        redis_mock = _make_redis_mock(allowed=0, remaining=0)
        app = create_rate_limit_test_app(redis_mock)

        mock_url_service = AsyncMock()
        mock_url_service.create.return_value = MagicMock(short_code="abc123")
        app.dependency_overrides[get_url_service] = lambda: mock_url_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/v0/shortner/",
                json={"target_url": "https://example.com"},
            )

        assert resp.status_code != 429
        redis_mock.eval.assert_not_called()


class TestSystemRoutesExempt:
    async def test_health_not_rate_limited(self, client: AsyncClient, redis_mock):
        resp = await client.get("/v0/system/health")
        redis_mock.eval.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/api/test_rate_limiter.py -v`
Expected: PASS

Note: Some tests may need adjustment based on the exact system router path and how the mock URL service interacts. Fix any test failures by adjusting mocks to match the actual endpoint behavior.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Run linter**

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: No issues (fix any that arise)

- [ ] **Step 5: Commit**

```bash
git add tests/api/test_rate_limiter.py
git commit -m "test: add API-level tests for rate limiter"
```

---

### Task 8: Final Verification

- [ ] **Step 1: Run the full test suite with coverage**

Run: `pytest tests/ -v --cov=src --cov-report=term-missing`
Expected: All tests pass, coverage >= 70%

- [ ] **Step 2: Run linter and formatter**

Run: `ruff check src/ tests/ && ruff format --check src/ tests/`
Expected: Clean

- [ ] **Step 3: Final commit if any formatting fixes were needed**

```bash
git add -A
git commit -m "chore: formatting fixes"
```
