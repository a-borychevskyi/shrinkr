# Rate Limiter Design Spec

## Overview

A custom Redis-based rate limiter for Shrinkr using the sliding window counter algorithm. Applied globally with per-route limits, configurable via environment variables with per-endpoint overrides through FastAPI's dependency injection.

## Decisions

- **Scope:** All API endpoints, with different limits per route. System endpoints (health, ready, metrics) are exempt.
- **Algorithm:** Sliding window counter — balances accuracy, memory efficiency, and fairness. Avoids boundary-burst problem of fixed windows without per-request storage cost of sliding log.
- **Client identification:** Proxy-aware IP extraction (`X-Forwarded-For` > `X-Real-IP` > `request.client.host`) with composite Redis key `{APP_PREFIX}:{rl_prefix}:{ip}:{route}` so limits are independent per endpoint.
- **Integration pattern:** Router-level dependency (Approach 3) — default `RateLimiter()` on API routers, per-endpoint override via `Depends(RateLimiter(times=X, seconds=Y))`, system routes on separate router with no limiter.
- **Atomicity:** Lua script executed via `redis.eval()` to make check-and-increment atomic under concurrent requests.

## Configuration

New `RateLimiterConfig` via pydantic-settings:

| Variable | Type | Default | Description |
|---|---|---|---|
| `RATE_LIMIT_DEFAULT_TIMES` | `int` | `60` | Max requests per window |
| `RATE_LIMIT_DEFAULT_WINDOW` | `int` | `60` | Window size in seconds |
| `RATE_LIMIT_ENABLED` | `bool` | `True` | Kill switch to disable globally |
| `RATE_LIMIT_KEY_PREFIX` | `str` | `"rl"` | Redis key namespace |

Per-endpoint overrides are code-level only (via `Depends(RateLimiter(times=10, seconds=60))`), not env vars.

## Client Identification

Utility function `get_client_ip(request: Request) -> str`:

1. Check `X-Forwarded-For` header — take the leftmost (first) IP (original client)
2. Fall back to `X-Real-IP` header
3. Fall back to `request.client.host`
4. Strip whitespace, validate non-empty

## Sliding Window Counter Algorithm

### How it works

Time is divided into fixed windows of `window` seconds. Two counters are tracked: current window and previous window. The estimated request count is:

```
estimate = prev_count * (1 - elapsed / window) + current_count
```

If `estimate >= limit`, the request is rejected with 429.

### Redis keys

Format: `{APP_PREFIX}:{RATE_LIMIT_KEY_PREFIX}:{ip}:{route}:{window_timestamp}`

Each key has a TTL of `2 * window` seconds (auto-cleanup — a counter only matters for its own window plus the next).

### Lua script

Executed atomically via `redis.eval()`:

1. Get counters for current and previous windows
2. Calculate weighted estimate
3. If under limit: increment current window counter, set TTL
4. Return `(allowed: 0|1, remaining: int, reset_at: int)`

## RateLimiter Dependency

Callable class compatible with FastAPI's `Depends()`:

```python
class RateLimiter:
    def __init__(self, times: int | None = None, seconds: int | None = None):
        # None = use defaults from RateLimiterConfig

    async def __call__(self, request: Request, redis: Redis = Depends(get_async_redis_client)):
        # 1. Check RATE_LIMIT_ENABLED
        # 2. Extract client IP
        # 3. Determine route pattern
        # 4. Run Lua script
        # 5. Attach rate limit headers to response
        # 6. If rejected: raise RateLimitExceeded
```

### Usage

Router-level default:
```python
v0_router = APIRouter(prefix="/v0", dependencies=[Depends(RateLimiter())])
```

Per-endpoint override:
```python
@router.post("/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def create_short_url(...):
```

## Response Headers

On all responses (success and 429):

- `X-RateLimit-Limit` — the limit for this endpoint
- `X-RateLimit-Remaining` — requests remaining
- `X-RateLimit-Reset` — Unix timestamp when current window resets

On 429 only:

- `Retry-After` — seconds until reset

## Exception

`RateLimitExceeded` extending `BaseApplicationException` with `status_code=429`. Handled by the existing `ExceptionHandler` — returns standard JSON error format.

## Observability

- OpenTelemetry span attributes: `rate_limit.key`, `rate_limit.allowed`, `rate_limit.remaining`, `rate_limit.client_ip`
- Loguru log on rejection: client IP, route, current count vs limit

## Files

### New files

| File | Purpose |
|---|---|
| `src/config/rate_limiter.py` | `RateLimiterConfig` pydantic-settings class |
| `src/utils/client_ip.py` | `get_client_ip()` function |
| `src/dependencies/rate_limiter.py` | `RateLimiter` callable class + Lua script |
| `src/utils/exceptions/rate_limit.py` | `RateLimitExceeded` exception |
| `tests/unit/test_client_ip.py` | Unit tests for IP extraction |
| `tests/unit/test_rate_limiter_config.py` | Unit tests for config |
| `tests/integration/test_rate_limiter.py` | Integration tests against real Redis |
| `tests/api/test_rate_limiter_api.py` | API-level tests for 429, headers, etc. |

### Modified files

| File | Change |
|---|---|
| `src/api/app.py` | Add `RateLimiter()` dependency to API routers |
| `src/utils/exceptions/__init__.py` | Export `RateLimitExceeded` |

## Testing

### Unit tests
- `get_client_ip()`: X-Forwarded-For, X-Real-IP, direct connection, multiple proxies, missing headers
- `RateLimiterConfig`: defaults, env var overrides, disabled flag
- Lua script logic: weighted calculation, boundary conditions

### Integration tests
- N requests allowed, (N+1)th rejected with 429
- Sliding window weighting from previous window
- Key isolation: different IPs and routes are independent
- TTL expiry after 2 * window
- `RATE_LIMIT_ENABLED=false` bypasses all checks

### API tests
- 429 response matches standard JSON error format
- Rate limit headers present on success
- `Retry-After` header on 429
- Router-level defaults apply
- Per-endpoint override takes precedence
