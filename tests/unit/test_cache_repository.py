from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import orjson
import pytest

from src.models.url.entity import UrlModel
from src.repositories.url import UrlCacheRepository

SAMPLE_URL = UrlModel(
    id=1,
    target_url="https://example.com",
    short_code="abc123",
    created_at=datetime(2026, 1, 1, tzinfo=UTC),
    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    deleted_at=None,
)

PREFIX = "shrinkr"


def _make_repo(redis_mock: AsyncMock | None = None) -> UrlCacheRepository:
    redis_client = redis_mock or AsyncMock()
    config = AsyncMock()
    config.APP_PREFIX = PREFIX
    return UrlCacheRepository(redis_client=redis_client, config=config)


class TestGetByShortCode:
    async def test_cache_miss_returns_none(self):
        redis = AsyncMock()
        redis.get.return_value = None
        repo = _make_repo(redis)

        result = await repo.get_by_short_code("abc123")

        assert result is None
        redis.get.assert_awaited_once_with(f"{PREFIX}:abc123")

    async def test_cache_hit_returns_model(self):
        redis = AsyncMock()
        redis.get.return_value = orjson.dumps(SAMPLE_URL.model_dump()).decode()
        repo = _make_repo(redis)

        result = await repo.get_by_short_code("abc123")

        assert result is not None
        assert result.short_code == "abc123"
        assert result.target_url == "https://example.com"
        assert result.id == 1

    async def test_cache_hit_preserves_all_fields(self):
        redis = AsyncMock()
        redis.get.return_value = orjson.dumps(SAMPLE_URL.model_dump()).decode()
        repo = _make_repo(redis)

        result = await repo.get_by_short_code("abc123")

        assert result is not None
        assert result.created_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert result.updated_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert result.deleted_at is None

    async def test_cache_miss_increments_miss_counter(self):
        redis = AsyncMock()
        redis.get.return_value = None
        repo = _make_repo(redis)

        with patch("src.repositories.url.cache_operations_total") as mock_counter:
            await repo.get_by_short_code("abc123")
            mock_counter.add.assert_called_with(
                1, attributes={"operation": "get", "result": "miss"}
            )

    async def test_cache_hit_increments_hit_counter(self):
        redis = AsyncMock()
        redis.get.return_value = orjson.dumps(SAMPLE_URL.model_dump()).decode()
        repo = _make_repo(redis)

        with patch("src.repositories.url.cache_operations_total") as mock_counter:
            await repo.get_by_short_code("abc123")
            mock_counter.add.assert_called_with(
                1, attributes={"operation": "get", "result": "hit"}
            )

    async def test_invalid_json_raises_error(self):
        redis = AsyncMock()
        redis.get.return_value = "not-valid-json"
        repo = _make_repo(redis)

        with pytest.raises(orjson.JSONDecodeError):
            await repo.get_by_short_code("abc123")

    async def test_empty_string_returns_none(self):
        redis = AsyncMock()
        redis.get.return_value = ""
        repo = _make_repo(redis)

        result = await repo.get_by_short_code("abc123")

        assert result is None

    async def test_key_uses_prefix(self):
        redis = AsyncMock()
        redis.get.return_value = None
        repo = _make_repo(redis)

        await repo.get_by_short_code("xyz789")

        redis.get.assert_awaited_once_with(f"{PREFIX}:xyz789")


class TestSetShortCode:
    async def test_set_stores_json(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        await repo.set_short_code("abc123", SAMPLE_URL)

        redis.set.assert_awaited_once()
        call_args = redis.set.call_args
        stored_key = call_args[0][0]
        stored_value = call_args[0][1]

        assert stored_key == f"{PREFIX}:abc123"
        parsed = orjson.loads(stored_value)
        assert parsed["short_code"] == "abc123"
        assert parsed["target_url"] == "https://example.com"

    async def test_set_applies_default_ttl(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        await repo.set_short_code("abc123", SAMPLE_URL)

        call_kwargs = redis.set.call_args.kwargs
        assert call_kwargs["ex"] == 60 * 60 * 6

    async def test_set_applies_custom_ttl(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        await repo.set_short_code("abc123", SAMPLE_URL, ttl=300)

        call_kwargs = redis.set.call_args.kwargs
        assert call_kwargs["ex"] == 300

    async def test_set_increments_counter(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        with patch("src.repositories.url.cache_operations_total") as mock_counter:
            await repo.set_short_code("abc123", SAMPLE_URL)
            mock_counter.add.assert_called_with(
                1, attributes={"operation": "set", "result": "ok"}
            )

    async def test_set_value_is_valid_json(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        await repo.set_short_code("abc123", SAMPLE_URL)

        stored_value = redis.set.call_args[0][1]
        model = UrlModel.model_validate(orjson.loads(stored_value))
        assert model.short_code == SAMPLE_URL.short_code
        assert model.target_url == SAMPLE_URL.target_url

    async def test_set_uses_atomic_ex(self):
        redis = AsyncMock()
        redis.set.return_value = True
        repo = _make_repo(redis)

        await repo.set_short_code("abc123", SAMPLE_URL, ttl=600)

        call_kwargs = redis.set.call_args.kwargs
        assert call_kwargs["ex"] == 600


class TestDeleteShortCode:
    async def test_delete_existing_key(self):
        redis = AsyncMock()
        redis.delete.return_value = 1
        repo = _make_repo(redis)

        result = await repo.delete_short_code("abc123")

        assert result == 1
        redis.delete.assert_awaited_once_with(f"{PREFIX}:abc123")

    async def test_delete_nonexistent_key(self):
        redis = AsyncMock()
        redis.delete.return_value = 0
        repo = _make_repo(redis)

        result = await repo.delete_short_code("missing")

        assert result == 0

    async def test_delete_key_uses_prefix(self):
        redis = AsyncMock()
        redis.delete.return_value = 1
        repo = _make_repo(redis)

        await repo.delete_short_code("xyz789")

        redis.delete.assert_awaited_once_with(f"{PREFIX}:xyz789")

    async def test_delete_existing_increments_ok_counter(self):
        redis = AsyncMock()
        redis.delete.return_value = 1
        repo = _make_repo(redis)

        with patch("src.repositories.url.cache_operations_total") as mock_counter:
            await repo.delete_short_code("abc123")
            mock_counter.add.assert_called_with(
                1, attributes={"operation": "delete", "result": "ok"}
            )

    async def test_delete_nonexistent_increments_miss_counter(self):
        redis = AsyncMock()
        redis.delete.return_value = 0
        repo = _make_repo(redis)

        with patch("src.repositories.url.cache_operations_total") as mock_counter:
            await repo.delete_short_code("missing")
            mock_counter.add.assert_called_with(
                1, attributes={"operation": "delete", "result": "miss"}
            )
