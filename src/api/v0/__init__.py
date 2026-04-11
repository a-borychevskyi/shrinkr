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
