from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from src.config.redis import RedisConfig
from src.di.clients.redis import get_async_redis_client
from src.repositories.url import UrlRepository, UrlCacheRepository


def get_url_repository():
    return UrlRepository()


def get_url_cache_repository(
    redis_client: Annotated[Redis, Depends(get_async_redis_client)],
):
    config = RedisConfig()
    return UrlCacheRepository(redis_client=redis_client, config=config)
