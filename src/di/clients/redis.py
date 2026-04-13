from functools import lru_cache

from redis.asyncio import Redis

from src.config.redis import RedisConfig


@lru_cache(maxsize=1)
def get_async_redis_client() -> Redis:
    """Return a process-wide async Redis client backed by a shared pool.

    Creating a fresh Redis instance per request (as FastAPI's Depends()
    does by default) builds a new connection pool each time, leaving
    old sockets in TIME_WAIT and exhausting the kernel's ephemeral
    port range under load. One client per worker reuses connections
    through the internal pool and keeps socket count bounded.
    """
    config = RedisConfig()
    return Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
        decode_responses=True,
    )
