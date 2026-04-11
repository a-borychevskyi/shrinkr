from redis.asyncio import Redis

from src.config.redis import RedisConfig


def get_async_redis_client() -> Redis:
    config = RedisConfig()
    return Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        db=config.REDIS_DB,
        password=config.REDIS_PASSWORD,
        decode_responses=True,
    )
