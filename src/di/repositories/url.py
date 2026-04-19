from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from src.config.redis import RedisConfig
from src.di.clients.redis import get_async_redis_client
from src.repositories.url import UrlCacheRepository, UrlRepository


@lru_cache(maxsize=1)
def get_redis_config() -> RedisConfig:
    """Cached provider for :class:`RedisConfig`.

    Constructing a pydantic-settings model parses the env each time;
    caching avoids doing that on every request in the redirect hot path.
    """
    return RedisConfig()


def get_url_repository():
    return UrlRepository()


def get_url_cache_repository(
    redis_client: Annotated[Redis, Depends(get_async_redis_client)],
):
    return UrlCacheRepository(redis_client=redis_client, config=get_redis_config())
