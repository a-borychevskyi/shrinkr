import pytest
from redis.asyncio import Redis

from src.config.redis import RedisConfig
from src.models.url.entity import UrlModel
from src.repositories.url import UrlCacheRepository


@pytest.fixture
def cache_repo(redis_client: Redis) -> UrlCacheRepository:
    config = RedisConfig(
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        REDIS_DB=0,
        APP_PREFIX="test",
    )
    return UrlCacheRepository(redis_client=redis_client, config=config)


def _make_url_model(short_code: str = "test123") -> UrlModel:
    return UrlModel(
        id=1,
        target_url="https://example.com",
        short_code=short_code,
    )


async def test_set_and_get(cache_repo: UrlCacheRepository):
    url = _make_url_model("cache1")
    await cache_repo.set_short_code("cache1", url)

    result = await cache_repo.get_by_short_code("cache1")
    assert result is not None
    assert result.target_url == "https://example.com"
    assert result.short_code == "cache1"


async def test_get_missing_key_returns_none(cache_repo: UrlCacheRepository):
    result = await cache_repo.get_by_short_code("nonexistent")
    assert result is None


async def test_delete_existing_key(cache_repo: UrlCacheRepository):
    url = _make_url_model("cache_del")
    await cache_repo.set_short_code("cache_del", url)

    deleted = await cache_repo.delete_short_code("cache_del")
    assert deleted == 1

    result = await cache_repo.get_by_short_code("cache_del")
    assert result is None


async def test_delete_missing_key_returns_zero(cache_repo: UrlCacheRepository):
    deleted = await cache_repo.delete_short_code("never_existed")
    assert deleted == 0


async def test_ttl_is_set(cache_repo: UrlCacheRepository, redis_client: Redis):
    url = _make_url_model("cache_ttl")
    await cache_repo.set_short_code("cache_ttl", url, ttl=300)

    ttl = await redis_client.ttl("test:cache_ttl")
    assert 0 < ttl <= 300


async def test_overwrite_existing_key(cache_repo: UrlCacheRepository):
    url1 = UrlModel(id=1, target_url="https://first.com", short_code="overwrite")
    url2 = UrlModel(id=1, target_url="https://second.com", short_code="overwrite")

    await cache_repo.set_short_code("overwrite", url1)
    await cache_repo.set_short_code("overwrite", url2)

    result = await cache_repo.get_by_short_code("overwrite")
    assert result is not None
    assert result.target_url == "https://second.com"


async def test_base_set_and_base_get(
    cache_repo: UrlCacheRepository, redis_client: Redis
):
    await cache_repo.base_set("raw_key", "raw_value")
    result = await cache_repo.base_get("raw_key")
    assert result == "raw_value"


async def test_set_expire(cache_repo: UrlCacheRepository, redis_client: Redis):
    await cache_repo.base_set("expire_key", "value")
    result = await cache_repo.set_expire("expire_key", 120)
    assert result is True
    ttl = await redis_client.ttl("test:expire_key")
    assert 0 < ttl <= 120
